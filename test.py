import telebot
from telebot import types
from settings import *

bot = telebot.TeleBot(TOKEN)

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

    # Envoyer le message avec le bouton fixe dans le canal
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
    button1 = types.InlineKeyboardButton(text="Problème de compte", callback_data='option_1')
    button2 = types.InlineKeyboardButton(text="Problème de livraison", callback_data='option_2')
    button3 = types.InlineKeyboardButton(text="Problème de paiement", callback_data='option_3')
    markup.add(button1, button2, button3)

    # Envoyer un message au chat privé de l'utilisateur avec les boutons
    bot.send_message(chat_id=call.from_user.id, text='Veuillez choisir une option :', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('option_'))
def process_option(call):
    # Récupérer l'option sélectionnée par l'utilisateur
    option = call.data.split('_')[1]

    # Traiter l'option
    # Vous pouvez ajouter votre logique de traitement ici

    # Envoyer une réponse à l'utilisateur
    bot.answer_callback_query(callback_query_id=call.id, text=f'Vous avez choisi l\'option {option}')

def process_ticket(ticket_info):
    # Logique de traitement du ticket
    # Vous pouvez envoyer les informations du ticket à un administrateur par exemple
    print('Nouveau ticket :', ticket_info)

bot.polling()
