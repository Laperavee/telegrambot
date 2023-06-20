import datetime
import time
import requests
import telebot
from telebot import types
from settings import *
import mysql.connector
conn = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)
bot = telebot.TeleBot(TOKEN)

ticketslist = []
tickets = {}

@bot.inline_handler(func=lambda query: True)
def inline_query(query):
    # Créer une nouvelle instance du message
    message = types.InputTextMessageContent('/ticket')

    # Créer une nouvelle réponse inline avec le message et l'ID de l'utilisateur
    inline_result = types.InlineQueryResultArticle(
        id='1',
        title='Ouvrir un ticket',
        input_message_content=message,
        description='Cliquez pour ouvrir un ticket'
    )

    # Envoyer la réponse inline à l'utilisateur
    bot.answer_inline_query(query.id, [inline_result])

@bot.message_handler(commands=['start'])
def start(message):
    # Créer un bouton fixe
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text='Ouvrir un ticket', callback_data='open_ticket')
    markup.add(button)
    # Envoyer le message avec le bouton fixe dans le canal d'origine
    bot.send_message(chat_id=message.chat.id, text='Cliquez sur le bouton pour ouvrir un ticket :', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'open_ticket')
def ticket(call):
    user_id = call.from_user.id
    cursor = conn.cursor()
    insert_query = '''SELECT * FROM user_timestamps WHERE user_id=%s ORDER BY start_timestamp DESC LIMIT 1'''
    cursor.execute(insert_query, (user_id,))
    result = cursor.fetchall()
    print(result)
    timestamp = result[0][2]
    time_elapsed = datetime.datetime.now() - timestamp
    if time_elapsed < datetime.timedelta(minutes=10):
        # Calculer les minutes restantes avant que l'utilisateur puisse ouvrir un autre ticket
        remaining_minutes = 10 - int(time_elapsed.total_seconds() // 60)

        # Envoyer un message indiquant à l'utilisateur d'attendre
        bot.send_message(chat_id=call.from_user.id,
                         text=f"Un ticket a été créé il y a {int(time_elapsed.total_seconds() // 60)} minutes. Veuillez attendre encore {remaining_minutes} minutes avant de créer un nouveau ticket.")
    else:
        bot.send_chat_action(call.from_user.id, 'typing')

        markup = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text="Problème de compte", callback_data='option_AccountProblem')
        button2 = types.InlineKeyboardButton(text="Problème de livraison", callback_data='option_DeliveryProblem')
        button3 = types.InlineKeyboardButton(text="Problème de paiement", callback_data='option_PaymentProblem')
        markup.add(button1)
        markup.add(button2)
        markup.add(button3)

        bot.send_message(chat_id=call.from_user.id, text='Veuillez choisir une option :', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('option_'))
def process_option(call):
    # Récupérer l'option sélectionnée par l'utilisateur
    option = call.data.split('_')[1]
    # Récupérer l'ID de l'utilisateur
    user_id = call.from_user.id
    username = call.from_user.username
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    # Envoyer une indication de saisie de texte à l'utilisateur
    bot.send_chat_action(call.from_user.id, 'typing')

    # Demander à l'utilisateur de saisir son problème
    bot.send_message(chat_id=call.from_user.id, text='Veuillez saisir votre problème :')

    # Ajouter l'option sélectionnée et l'ID de l'utilisateur au dictionnaire des tickets en attente
    tickets[call.from_user.id] = {'option': option, 'username': username, 'user_id':user_id}


@bot.message_handler(func=lambda message: message.chat.id in tickets)
def process_ticket_message(message):
    # Récupérer le ticket en attente pour l'utilisateur
    ticket = tickets[message.chat.id]
    # Enregistrer la description du problème dans le ticket
    ticket['description'] = message.text
    ticket['id'] = len(ticketslist)
    # Supprimer le ticket en attente de la liste des tickets
    del tickets[message.chat.id]

    # Traiter le ticket
    process_ticket(ticket)

    # Envoyer une réponse à l'utilisateur
    bot.send_message(chat_id=message.chat.id, text='Votre ticket a été enregistré.')

def process_ticket(ticket_info):
    # Logique de traitement du ticket
    # Vous pouvez enregistrer le ticket dans une base de données, l'envoyer à un administrateur, etc.
    cursor = conn.cursor()
    insert_query = '''INSERT INTO tickets (option_name, description, username) VALUES (%s, %s, %s)'''
    username = ticket_info['username']
    ticket_values = (ticket_info['option'], ticket_info['description'],username)
    cursor.execute(insert_query, ticket_values)
    conn.commit()
    cursor = conn.cursor()
    insert_query = '''INSERT INTO user_timestamps (user_id, start_timestamp) VALUES (%s, %s)'''
    user_id = ticket_info['user_id']
    time_stamp = datetime.datetime.now()
    print(user_id,time_stamp)
    cursor.execute(insert_query, (user_id,time_stamp))
    conn.commit()
    print('Nouveau ticket :', ticket_info)


@bot.message_handler(commands=['tickets'])
def show_tickets(message):
    # Vérifier l'ID du canal
    if message.chat.id != CHANNEL_ID:
        bot.send_message(chat_id=message.chat.id, text='Désolé, cette commande n\'est pas autorisée dans ce canal.')
        return

    cursor = conn.cursor()

    select_query = '''
    SELECT id, option_name, description, username
    FROM tickets
    '''
    cursor.execute(select_query)

    tickets = cursor.fetchall()
    # Créer un bouton pour chaque ticket enregistré
    markup = types.InlineKeyboardMarkup()

    for ticket in tickets:
        ticket_id = ticket[0]
        button = types.InlineKeyboardButton(text=str(ticket_id), callback_data=f'show_ticket_{ticket_id}')
        markup.row(button)  # Ajouter le bouton à une nouvelle ligne dans le markup

    # Envoyer les boutons dans le chat d'origine
    bot.send_message(chat_id=CHANNEL_ID, text='Liste des tickets :', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('show_ticket_'))
def show_ticket(call):
    # Récupérer l'ID du ticket à afficher
    ticket_id = call.data.split('_')[-1]
    cursor = conn.cursor()
    select_query = '''
        SELECT id, option_name, description, username
        FROM tickets WHERE id= %s
        '''

    cursor.execute(select_query,(ticket_id,))

    ticket = cursor.fetchall()
    # Vérifier si le ticket existe
    if ticket:
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")
        # Envoyer l'intitulé et la description du ticket
        bot.send_message(chat_id=call.from_user.id,
                         text=f"Option : {ticket[0][1]}\nDescription : {ticket[0][2]}\nUsername : {ticket[0][3]}")

        # Créer un bouton pour démarrer le chat privé
        markup = types.InlineKeyboardMarkup()
        buttonChat = types.InlineKeyboardButton(
            text="Commencer le chat privé",
            url=f"https://t.me/{ticket[0][3]}"
        )
        buttonDelete = types.InlineKeyboardButton(text="Supprimer le ticket", callback_data=f'delete_ticket_{ticket_id}')
        buttonGiveCompte = types.InlineKeyboardButton(text="Redonner un compte", callback_data=f'regive_account_{ticket[0][3]}_{ticket_id}')
        markup.add(buttonChat)
        markup.add(buttonDelete)
        markup.add(buttonGiveCompte)
        # Envoyer le bouton dans le chat d'origine
        bot.send_message(chat_id=call.from_user.id, text="Actions",
                         reply_markup=markup)
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")

    else:
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")
        # Envoyer un message d'erreur si le ticket n'existe pas
        bot.send_message(chat_id=call.from_user.id, text='Ticket non trouvé.')
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_ticket'))
def delete_ticket(call):
    # Récupérer l'ID du ticket à afficher
    ticket_id = call.data.split('_')[-1]
    cursor = conn.cursor()
    select_query = '''
            DELETE FROM tickets
             WHERE id= %s
            '''

    cursor.execute(select_query, (ticket_id,))
    conn.commit()
    bot.send_message(chat_id=call.from_user.id, text='Ticket supprimé')
    bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('regive_account'))
def regive_account(call):
    # Récupérer l'ID du ticket à afficher
    ticket_username = call.data.split('_')[-2]
    cursor = conn.cursor()
    select_query = '''
           INSERT INTO givecompte (username) VALUES (%s)
            '''

    cursor.execute(select_query, (ticket_username,))
    conn.commit()

    bot.send_message(chat_id=call.from_user.id, text='Compte à donner enregistré')
    delete_ticket(call)

@bot.message_handler(commands=['comptes'])
def accounts_to_give(message):
    # Vérifier l'ID du canal
    if message.chat.id != CHANNEL_ID:
        bot.send_message(chat_id=message.chat.id, text='Désolé, cette commande n\'est pas autorisée dans ce canal.')
        return

    cursor = conn.cursor()

    select_query = '''
    SELECT id, username
    FROM givecompte 
    '''
    cursor.execute(select_query)

    tickets = cursor.fetchall()
    # Créer un bouton pour chaque ticket enregistré
    markup = types.InlineKeyboardMarkup()

    for ticket in tickets:
        ticket_id = ticket[0]
        ticket_name = ticket[1]
        button = types.InlineKeyboardButton(text=str(ticket_name), callback_data=f'show_compte_{ticket_name}_{ticket_id}')
        markup.row(button)  # Ajouter le bouton à une nouvelle ligne dans le markup

    # Envoyer les boutons dans le chat d'origine
    bot.send_message(chat_id=CHANNEL_ID, text='Liste des comptes :', reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data.startswith('show_compte'))
def show_compte(call):
    # Récupérer l'ID du ticket à afficher
    ticket_id = call.data.split('_')[-1]
    ticket_name = call.data.split('_')[-2]
    cursor = conn.cursor()
    select_query = '''
        SELECT id, username
        FROM givecompte WHERE id= %s
        '''

    cursor.execute(select_query,(ticket_id,))
    ticket = cursor.fetchall()
    select_query = '''
            SELECT COUNT(*)
            FROM givecomptearchive WHERE username= %s
            '''

    cursor.execute(select_query, (ticket_name,))
    nbcompte = cursor.fetchone()
    # Vérifier si le ticket existe
    if ticket:
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")
        # Envoyer l'intitulé et la description du ticket
        bot.send_message(chat_id=call.from_user.id,
                         text=f"Username : {ticket[0][1]}")
        bot.send_message(chat_id=call.from_user.id,
                         text=f"Cette personne a déjà demandé {nbcompte[0]} compte(s)")
        # Créer un bouton pour démarrer le chat privé
        markup = types.InlineKeyboardMarkup()
        buttonChat = types.InlineKeyboardButton(
            text="Commencer le chat privé",
            url=f"https://t.me/{ticket_name}"
        )
        buttonDeleteWithout = types.InlineKeyboardButton(text="Supprimer le ticket SANS compte", callback_data=f'delete_compte_{False}_{ticket_name}_{ticket_id}')
        buttonDeleteWith = types.InlineKeyboardButton(text="Supprimer le ticket AVEC compte", callback_data=f'delete_compte_{True}_{ticket_name}_{ticket_id}')
        markup.add(buttonDeleteWithout)
        markup.add(buttonDeleteWith)
        markup.add(buttonChat)
        # Envoyer le bouton dans le chat d'origine
        bot.send_message(chat_id=call.from_user.id, text="Actions",
                         reply_markup=markup)
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")
    else:
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")
        # Envoyer un message d'erreur si le ticket n'existe pas
        bot.send_message(chat_id=call.from_user.id, text='Ticket non trouvé.')
        bot.send_message(chat_id=call.from_user.id,
                         text="------------------")

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_compte'))
def delete_compte(call):
    # Récupérer l'ID du ticket à afficher
    ticket_id = call.data.split('_')[-1]
    ticket_name = call.data.split('_')[-2]
    ticket_compte = call.data.split('_')[-3]
    if(ticket_compte==True):
        cursor = conn.cursor()
        select_query = '''
                    INSERT INTO givecomptearchive (username) VALUES (%s)
                    '''

        cursor.execute(select_query, (ticket_name,))
        conn.commit()
    cursor = conn.cursor()
    select_query = '''
            DELETE FROM givecompte
             WHERE id= %s
            '''

    cursor.execute(select_query, (ticket_id,))
    conn.commit()
    bot.send_message(chat_id=call.from_user.id, text='Ticket supprimé')
    bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

bot.polling()