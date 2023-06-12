import telebot
import ast
import time
import requests
from telebot import types
from settings import *

bot = telebot.TeleBot(TOKEN)
tickets = {}
stringList = {"Name": "John", "Language": "Python", "API": "pyTelegramBotAPI"}
crossIcon = u"\u274C"
ticket_id_counter = 1

def makeKeyboard():
    markup = types.InlineKeyboardMarkup()

    for key, value in stringList.items():
        markup.add(types.InlineKeyboardButton(text=value,
                                              callback_data="['value', '" + value + "', '" + key + "']"),
                   types.InlineKeyboardButton(text=crossIcon,
                                              callback_data="['key', '" + key + "']"))

    return markup

def generate_ticket_id():
    global ticket_id_counter
    ticket_id = ticket_id_counter
    ticket_id_counter += 1
    return str(ticket_id)

def create_ticket(user_id, description):
    ticket_id = generate_ticket_id()
    tickets[ticket_id] = {
        'user_id': user_id,
        'description': description,
        'status': 'Open'
    }
    return ticket_id

@bot.message_handler(commands=['test'])
def handle_command_adminwindow(message):
    bot.send_message(chat_id=message.chat.id,
                     text="Here are the values of stringList",
                     reply_markup=makeKeyboard(),
                     parse_mode='HTML')

@bot.message_handler(commands=['topic'])
def create_topic(message):
    topic = "Nouveau topic"
    chat_id = 123456789  # Remplacez par l'ID du chat ou du topic spécifique

    # Créer le lien d'invitation vers le topic
    invite_link = bot.create_chat_invite_link(chat_id)

    # Envoyer le lien d'invitation au chat ou au topic spécifique
    bot.send_message(chat_id, f"Voici le lien d'invitation vers le topic '{topic}': {invite_link.invite_link}")

@bot.message_handler(commands=['ticket'])
def create_ticket_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    description = message.text.split('/ticket', 1)[1].strip()
    ticket_id = create_ticket(user_id, description)
    bot.send_message(chat_id, f"Ticket created! Ticket ID: {ticket_id}")

@bot.message_handler(commands=['status'])
def ticket_status_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    ticket_id = message.text.split('/status', 1)[1].strip()
    ticket = tickets.get(ticket_id)
    if ticket and ticket['user_id'] == user_id:
        status = ticket['status']
        bot.send_message(chat_id, f"Ticket ID: {ticket_id}\nStatus: {status}")
    else:
        bot.send_message(chat_id, "Invalid ticket ID or you don't have access to this ticket.")

@bot.message_handler(commands=['close'])
def close_ticket_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    ticket_id = message.text.split('/close', 1)[1].strip()
    ticket = tickets.get(ticket_id)
    if ticket and ticket['user_id'] == user_id:
        ticket['status'] = 'Closed'
        bot.send_message(chat_id, f"Ticket ID: {ticket_id} closed successfully.")
    else:
        bot.send_message(chat_id, "Invalid ticket ID or you don't have access to this ticket.")

@bot.message_handler(commands=['tickets'])
def list_tickets_handler(message):
    chat_id = message.chat.id

    if len(tickets) == 0:
        bot.send_message(chat_id, "Aucun ticket ouvert.")
    else:
        markup = types.InlineKeyboardMarkup()

        for ticket_id, ticket_data in tickets.items():
            button_text = f"Ticket ID: {ticket_id}"
            callback_data = f"['ticket', '{ticket_id}']"
            markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

        bot.send_message(chat_id, "Tickets ouverts :", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith("['value'"):
        valueFromCallBack = ast.literal_eval(call.data)[1]
        keyFromCallBack = ast.literal_eval(call.data)[2]
        bot.answer_callback_query(callback_query_id=call.id,
                              show_alert=True,
                              text="You Clicked " + valueFromCallBack + " and key is " + keyFromCallBack)

    if call.data.startswith("['key'"):
        keyFromCallBack = ast.literal_eval(call.data)[1]
        del stringList[keyFromCallBack]
        bot.edit_message_text(chat_id=call.message.chat.id,
                              text="Here are the values of stringList",
                              message_id=call.message.message_id,
                              reply_markup=makeKeyboard(),
                              parse_mode='HTML')

    if call.data.startswith("['ticket'"):
        ticket_id = ast.literal_eval(call.data)[1]
        ticket = get_ticket_by_id(ticket_id)
        if ticket:
            user_id = call.from_user.id
            if ticket['user_id'] == user_id:
                message = f"Ticket ID: {ticket_id}\n" \
                          f"Description: {ticket['description']}\n" \
                          f"Status: {ticket['status']}"
                bot.send_message(call.message.chat.id, message)
            else:
                bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text="Vous n'avez pas accès à ce ticket.")
        else:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text="ID de ticket invalide.")

def get_ticket_by_id(ticket_id):
    for ticket in tickets.values():
        if ticket['status'] != 'Closed' and ticket_id == str(ticket_id):
            return ticket
    return None

while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=0)
    except:
        time.sleep(10)
