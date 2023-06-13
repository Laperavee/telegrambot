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
    # Récupérer l'ID de l'utilisateur qui a appuyé sur le bouton
    user_id = query.from_user.id

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
    # Récupérer les informations du ticket
    user_id = call.from_user.id
    user_name = call.from_user.username
    ticket_id = user_id  # Utiliser l'ID de l'utilisateur comme ID du ticket (vous pouvez utiliser une logique différente)

    # Envoyer une indication de saisie de texte à l'utilisateur
    bot.send_chat_action(call.from_user.id, 'typing')

    # Créer les boutons pour les options du ticket
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="Problème de compte", callback_data='option_AccountProblem')
    button2 = types.InlineKeyboardButton(text="Problème de livraison", callback_data='option_DeliveryProblem')
    button3 = types.InlineKeyboardButton(text="Problème de paiement", callback_data='option_PaymentProblem')
    markup.add(button1)
    markup.add(button2)
    markup.add(button3)

    # Envoyer un message au chat privé de l'utilisateur avec les boutons
    bot.send_message(chat_id=call.from_user.id, text='Veuillez choisir une option :', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('option_'))
def process_option(call):
    # Récupérer l'option sélectionnée par l'utilisateur
    option = call.data.split('_')[1]

    # Récupérer l'ID de l'utilisateur
    user_id = call.from_user.id

    # Envoyer une indication de saisie de texte à l'utilisateur
    bot.send_chat_action(call.from_user.id, 'typing')

    # Demander à l'utilisateur de saisir son problème
    bot.send_message(chat_id=call.from_user.id, text='Veuillez saisir votre problème :')

    # Ajouter l'option sélectionnée et l'ID de l'utilisateur au dictionnaire des tickets en attente
    tickets[call.from_user.id] = {'option': option, 'user_id': user_id}


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
    process_ticket(ticket,ticketslist)

    # Envoyer une réponse à l'utilisateur
    bot.send_message(chat_id=message.chat.id, text='Votre ticket a été enregistré.')

def process_ticket(ticket_info, ticketslist):
    # Logique de traitement du ticket
    # Vous pouvez enregistrer le ticket dans une base de données, l'envoyer à un administrateur, etc.
    cursor = conn.cursor()
    insert_query = '''
    INSERT INTO tickets (option_name, description, user_id)
    VALUES (%s, %s, %s)
    '''
    user_id = ticket_info['user_id']
    print(user_id)
    ticket_values = (ticket_info['option'], ticket_info['description'],user_id)

    cursor.execute(insert_query, ticket_values)

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
    SELECT id, option_name, description, user_id
    FROM tickets
    '''
    cursor.execute(select_query)

    tickets = cursor.fetchall()
    print(tickets)
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
    print("ticket_show",ticket_id)
    select_query = '''
        SELECT id, option_name, description, user_id
        FROM tickets WHERE id= %s
        '''

    cursor.execute(select_query,(ticket_id,))

    ticket = cursor.fetchall()
    # Récupérer le ticket correspondant
    print(ticket)
    # Vérifier si le ticket existe
    if ticket:
        print(ticket)
        # Envoyer l'intitulé et la description du ticket
        bot.send_message(chat_id=call.from_user.id,
                         text=f"Option : {ticket[0][1]}\nDescription : {ticket[0][2]}\nIdUser : {ticket[0][3]}")

        # Créer un bouton pour démarrer le chat privé
        markup = types.InlineKeyboardMarkup()
        buttonChat = types.InlineKeyboardButton(text="Commencer le chat privé", callback_data='private_chat')
        buttonDelete = types.InlineKeyboardButton(text="Supprimer le ticket", callback_data=f'delete_ticket_{ticket_id}')
        markup.add(buttonChat)
        markup.add(buttonDelete)
        # Envoyer le bouton dans le chat d'origine
        bot.send_message(chat_id=call.from_user.id, text="Actions",
                         reply_markup=markup)

    else:
        # Envoyer un message d'erreur si le ticket n'existe pas
        bot.send_message(chat_id=call.from_user.id, text='Ticket non trouvé.')

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


def create_private_chat(user_id, bot_id):
    # Endpoint de l'API Telegram pour créer une discussion privée
    endpoint = f"https://api.telegram.org/bot{TOKEN}/createChat"

    # Paramètres de la requête
    params = {
        'user_id': user_id,
        'bot': bot_id
    }

    # Envoyer la requête
    response = requests.get(endpoint, params=params)

    # Vérifier la réponse de l'API Telegram
    if response.status_code == 200:
        # La discussion privée a été créée avec succès
        print("Discussion privée créée avec succès.")
    else:
        # Une erreur s'est produite lors de la création de la discussion privée
        print("Erreur lors de la création de la discussion privée.")

bot.polling()