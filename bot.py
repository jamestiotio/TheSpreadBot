# coding=utf-8
# Written by James Raphael Tiovalen - @jamestiotio (2019)
"""Only for use by The Spread @ NUS Business School, Singapore to
provide its Telegram Bot services - @TheSpreadBot"""

# Import libraries
import sys
import logging
import os
import math
from decimal import Decimal
from io import BytesIO
from datetime import datetime
from functools import wraps
from tabulate import tabulate
from PIL import Image
import requests
import ast
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, \
    CallbackQueryHandler, PreCheckoutQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, \
    KeyboardButton, ReplyKeyboardMarkup, LabeledPrice
from dbhelper import DBHelper

# Initialize global variables
BOT_TOKEN = os.environ['BOT_TOKEN']
SUPER_ADMIN = ast.literal_eval(os.environ['SUPER_ADMIN'])
ADMIN_LIST = ast.literal_eval(os.environ['ADMIN_LIST'])
bot = telegram.Bot(token=BOT_TOKEN)
# Create the EventHandler and pass it the bot's token.
updater = Updater(token=BOT_TOKEN)
db = DBHelper()

PORT = int(os.environ.get('PORT', '5000'))
WEBHOOK_URL = os.environ['WEBHOOK_URL']

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s -'
                           '%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# For ConversationHandler purposes
QUANTITY, REMARKS, FULL_NAME, CONTACT_NUMBER, LOCATION, COLLECTION_TIME, \
 RECEIPT_IMAGE, EDIT_MENU = range(8)

# Global variables to store the menu (and for InlineButtons)
monday_list = [db.check_menu('MONDAY')]
tuesday_list = [db.check_menu('TUESDAY')]
wednesday_list = [db.check_menu('WEDNESDAY')]
thursday_list = [db.check_menu('THURSDAY')]
friday_list = [db.check_menu('FRIDAY')]

# Menu strings
monday_menu = '\r\n'.join(['<pre>• ' + str(monday_list[0][0][i]) + ' - $' +
                           str(monday_list[0][1][i]) + '</pre>'
                           for i in range(len(monday_list[0][0]))])
tuesday_menu = '\r\n'.join(['<pre>• ' + str(tuesday_list[0][0][i]) + ' - $' +
                            str(tuesday_list[0][1][i]) + '</pre>'
                            for i in range(len(tuesday_list[0][0]))])
wednesday_menu = '\r\n'.join(['<pre>• ' + str(wednesday_list[0][0][i]) + ' - $'
                              + str(wednesday_list[0][1][i]) + '</pre>'
                              for i in range(len(wednesday_list[0][0]))])
thursday_menu = '\r\n'.join(['<pre>• ' + str(thursday_list[0][0][i]) + ' - $' +
                             str(thursday_list[0][1][i]) + '</pre>'
                             for i in range(len(thursday_list[0][0]))])
friday_menu = '\r\n'.join(['<pre>• ' + str(friday_list[0][0][i]) + ' - $' +
                           str(friday_list[0][1][i]) + '</pre>'
                           for i in range(len(friday_list[0][0]))])


# Start to define functions

# Only accessible if `user_id` is in `SUPER_ADMIN`
def super_restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in SUPER_ADMIN:
            print('Unauthorized superuser access denied for user {}.'
                  .format(user_id))
            return
        return func(bot, update, *args, **kwargs)

    return wrapped


# Only accessible if `user_id` is in `ADMIN_LIST`
def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_LIST:
            print('Unauthorized admin access denied for user {}.'
                  .format(user_id))
            return
        return func(bot, update, *args, **kwargs)

    return wrapped


# Only functional during operating time
def operating_time(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        weekday = datetime.now().weekday()
        hour = datetime.now().hour
        operating_days = list(range(0, 5))
        operating_hours = list(range(8, 21))
        if weekday not in operating_days or hour not in operating_hours:
            reply_markup = telegram.ReplyKeyboardRemove()
            print('Out of operating time request by user {}.'
                  .format(user_id))
            bot.send_message(chat_id=update.message.chat_id,
                             text='We are currently closed. Please contact '
                                  'us during our operating hours. Thank you '
                                  'for your understanding!',
                             reply_markup=reply_markup)
            return
        return func(bot, update, *args, **kwargs)

    return wrapped


@super_restricted
def root(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text='This text is meant to be sent only to this bot\'s '
                          'superadmin. If you manage to find this, '
                          'congratulations! You broke the bot! Please inform '
                          '@jamestiotio immediately about this issue. '
                          'Thank you!')


@restricted
def purge(bot, update):
    db.purge_order_list()
    bot.send_message(chat_id=update.message.chat_id,
                     text='Order list has been successfully purged!\r\n\r\n'
                          'Please purge the order list daily so as to '
                          'prevent too much lag. Thank you!')


@restricted
def vieworderlist(bot, update):
    order_list = db.retrieve_current_orders()
    reply_markup = telegram.ReplyKeyboardRemove()
    for i in order_list:
        collection_time = str(i[0])
        user_id = str(i[1])
        contact_number = str(i[4])
        item_ordered = str(i[5])
        quantity = str(i[6])
        location = str(i[7])
        remarks = str(i[8])
        receipt = BytesIO(i[10])
        receipt.seek(0)
        bot.send_photo(chat_id=update.effective_user.id,
                       caption='{} - {}, {}: {} x{} at {}. {}'
                               .format(collection_time, user_id, contact_number, item_ordered, quantity, location, remarks),
                       photo=receipt,
                       reply_markup=reply_markup,
                       disable_notification=True)


@restricted
def editmenu(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text='Please send a photo with a caption following this template:\r\n\r\n'
                          '<category> - <name> - <price>')

    return EDIT_MENU


def menu_editor(bot, update):
    if len(update.message.caption.split(' - ')) != 3:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Please follow the aforementioned message format!')
    else:
        item_image = bot.get_file(update.message.photo[-1].file_id)['file_path']
        response = requests.get(item_image)
        category = str(update.message.caption.split(' - ')[0]).upper()
        name = str(" ".join(w.capitalize() for w in str(update.message.caption.split(' - ')[1]).split()))
        price = Decimal('{}'.format(update.message.caption.split(' - ')[2])).__round__(2)
        db.edit_menu(name, response.content, price, category)
        bot.send_message(chat_id=update.message.chat_id,
                        text='{}\'s menu has been updated!'.format(category.capitalize()))

        return ConversationHandler.END


@restricted
def delete_paid(bot, update, args):
    try:
        user_id = int(args[0])
        db.delete_paid_user(user_id)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Paid orders from user {} has been deleted, if any.'.format(user_id))
    except IndexError:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Please specify the User ID of whom delivered orders you are deleting!\r\n\r\n'
                              'Template:\r\n/deletepaiduser <user_id>')
    except ValueError:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Please enter a valid User ID integer value!')


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


# Function to start the bot, initiated on /start command
def start(bot, update):
    username = update.message.from_user.username if \
        update.message.from_user.username else \
        update.message.from_user.first_name
    user_id = update.effective_user.id
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='Hi @{}, I am a bot that helps you place your order '
                          'at The Spread.\r\n\r\n'
                          '• /menu to check the menu.\r\n'
                          '• /order to place your order.\r\n'
                          '• /cart to check your cart.\r\n'
                          '• /offers to view available deals.\r\n'
                          '• /pay to proceed to payment.\r\n'
                          '• /cancel to cancel your order.\r\n'
                          '• /terms to read our Terms & Conditions.\r\n\r\n'
                          'Our operating hours is on 0800-2100hrs during '
                          'weekdays.\r\n\r\n'
                          'By interacting with this bot, you confirm '
                          'your consent to our Terms & Conditions. '
                          'If you need support, please contact us '
                          'at +6569085955.'.format(username),
                     reply_markup=reply_markup)

    if user_id in ADMIN_LIST:
        bot.send_message(chat_id=update.message.chat_id,
                         text='These are the possible admin commands:\r\n\r\n'
                              '• /purge to purge the order list.\r\n'
                              '• /editmenu to edit the menu options.\r\n'
                              '• /deletepaiduser <user_id> to delete the delivered orders of a specific user.\r\n'
                              '• /vieworderlist to display the current order list.\r\n')


def terms(bot, update):
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
                     text='<b>TERMS & CONDITIONS</b>\r\n\r\n'
                          '1. All prices are quoted in 🇸🇬Singapore '
                          'dollars, unless otherwise stated.\r\n\r\n'
                          '2. Discounts, offers, prizes, gifts, '
                          'complimentary items, vouchers, rebates, '
                          'redemptions and privileges are '
                          'non-redeemable for cash, non-transferable, '
                          'non-assignable and non-exchangeable. Prizes,'
                          ' gifts, complimentary items, vouchers, '
                          'rebate letters and redemption letters are '
                          'non-replaceable if lost, stolen or damaged.'
                          '\r\n\r\n3. Offers are not valid with other '
                          'on-going promotions, discounts, vouchers, '
                          'rebates, privilege cards, loyalty '
                          'programmes, set-menus, in-house offers, '
                          'functions, banquets or catering functions, '
                          'unless otherwise stated.\r\n\r\n4. The Spread '
                          'may vary these terms & conditions or '
                          'discontinue any promotions/privileges at '
                          'any time without any notice or liability '
                          'to any party.\r\n\r\n5. The Spread\'s decision '
                          'on all matters relating to its discounts, '
                          'offers, prizes, gifts, complimentary items, '
                          'vouchers, rebates, redemptions and '
                          'privileges shall be final and binding.\r\n\r\n'
                          '6. The Spread is not responsible for any misuse '
                          'or abuse of this bot. The onus is on the customer'
                          ' to utilize the bot properly.\r\n\r\n'
                          '7. The Spread ensures that all information '
                          'is securely transmitted through this '
                          'official bot and is only used for ordering '
                          'purposes. Only The Spread and the customer can '
                          'access these confidential information.\r\n\r\n'
                          '8. All information is correct at time of print.',
                     reply_markup=reply_markup)


# Function to send menu
def menu(bot, update):
    reply_markup = telegram.ReplyKeyboardRemove()

    bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
                     disable_notification=False,
                     text='<b>CURRENT WEEKLY MENU</b>\r\n\r\n'
                          '<b>MONDAY</b>\r\n{}\r\n\r\n'
                          '<b>TUESDAY</b>\r\n{}\r\n\r\n'
                          '<b>WEDNESDAY</b>\r\n{}\r\n\r\n'
                          '<b>THURSDAY</b>\r\n{}\r\n\r\n'
                          '<b>FRIDAY</b>\r\n{}\r\n\r\n'
                     .format(str(monday_menu), str(tuesday_menu),
                             str(wednesday_menu), str(thursday_menu),
                             str(friday_menu)),
                     reply_markup=reply_markup)


# Build the inline menu
def build_menu(buttons, n_cols, header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


# Function for ordering food
@operating_time
def order(bot, update):
    current_day = datetime.now().weekday()
    button_labels = []
    if current_day == 0:  # Monday
        button_labels.append(['😭 Monday'])
    elif current_day == 1:  # Tuesday
        button_labels.append(['😞 Tuesday'])
    elif current_day == 2:  # Wednesday
        button_labels.append(['😕 Wednesday'])
    elif current_day == 3:  # Thursday
        button_labels.append(['😬 Thursday'])
    elif current_day == 4:  # Friday
        button_labels.append(['😍 Friday'])
    reply_keyboard = telegram.ReplyKeyboardMarkup(button_labels,
                                                  resize_keyboard=True)
    bot.send_chat_action(chat_id=update.effective_user.id,
                         action=telegram.ChatAction.TYPING)
    bot.send_message(chat_id=update.effective_user.id,
                     text='Which category would you like to order?',
                     reply_markup=reply_keyboard)


# Function to ask user about category of food he/she wants to order
def food_category(bot, update):
    if update.message.text == '😭 Monday':
        monday(bot, update)
    elif update.message.text == '😞 Tuesday':
        tuesday(bot, update)
    elif update.message.text == '😕 Wednesday':
        wednesday(bot, update)
    elif update.message.text == '😬 Thursday':
        thursday(bot, update)
    elif update.message.text == '😍 Friday':
        friday(bot, update)


def monday(bot, update):
    monday = db.check_photo("MONDAY")[0]
    bio = BytesIO(monday)
    bio.seek(0)
    button_list = [InlineKeyboardButton(str(i), callback_data=str(i))
                   for i in monday_list[0][0]]
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='You have selected the Monday category.',
                     reply_markup=reply_markup)
    bot.send_photo(chat_id=update.effective_user.id,
                   photo=bio)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text='Monday\'s menu is:',
                     reply_markup=reply_markup)


def tuesday(bot, update):
    tuesday = db.check_photo("TUESDAY")[0]
    bio = BytesIO(tuesday)
    bio.seek(0)
    button_list = [InlineKeyboardButton(str(i), callback_data=str(i))
                   for i in tuesday_list[0][0]]
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='You have selected the Tuesday category.',
                     reply_markup=reply_markup)
    bot.send_photo(chat_id=update.effective_user.id,
                   photo=bio)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text='Tuesday\'s menu is:',
                     reply_markup=reply_markup)


def wednesday(bot, update):
    wednesday = db.check_photo("WEDNESDAY")[0]
    bio = BytesIO(wednesday)
    bio.seek(0)
    button_list = [InlineKeyboardButton(str(i), callback_data=str(i))
                   for i in wednesday_list[0][0]]
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='You have selected the Wednesday category.',
                     reply_markup=reply_markup)
    bot.send_photo(chat_id=update.effective_user.id,
                   photo=bio)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text='Wednesday\'s menu is:',
                     reply_markup=reply_markup)


def thursday(bot, update):
    thursday = db.check_photo("THURSDAY")[0]
    bio = BytesIO(thursday)
    bio.seek(0)
    button_list = [InlineKeyboardButton(str(i), callback_data=str(i))
                   for i in thursday_list[0][0]]
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='You have selected the Thursday category.',
                     reply_markup=reply_markup)
    bot.send_photo(chat_id=update.effective_user.id,
                   photo=bio)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text='Thursday\'s menu is:',
                     reply_markup=reply_markup)


def friday(bot, update):
    friday = db.check_photo("FRIDAY")[0]
    bio = BytesIO(friday)
    bio.seek(0)
    button_list = [InlineKeyboardButton(str(i), callback_data=str(i))
                   for i in friday_list[0][0]]
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='You have selected the Friday category.',
                     reply_markup=reply_markup)
    bot.send_photo(chat_id=update.effective_user.id,
                   photo=bio)
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text='Friday\'s menu is:',
                     reply_markup=reply_markup)


# Function to choose quantity
@operating_time
def quantity(bot, update):
    query = update.callback_query
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    db.add_order(user_id, username, first_name, query.data)
    bot.answer_callback_query(query.id)
    bot.edit_message_text(chat_id=query.message.chat_id,
                          text='Please enter the quantity for the item'
                               ' that you ordered.',
                          message_id=query.message.message_id)

    return QUANTITY


# Function to add remarks for the ordered item
@operating_time
def remarks(bot, update):
    try:
        quantity = int(update.message.text)
        user_id = update.effective_user.id
        item_ordered = str(db.select_latest_item(user_id))[2:-2]
        db.add_quantity(quantity, user_id, item_ordered)
        bot.send_message(chat_id=update.message.chat_id,
                         text='You have ordered {} {}.'.format(quantity,
                                                               item_ordered))
        extras = []
        if item_ordered == 'Double-Decker White Sandwich':
            extras.append(['Egg Salad'])
            extras.append(['Tuna Mayo'])
        if item_ordered == 'Penne Quattro Formaggi (4 Cheeses)':
            extras.append(['+ Smoked Turkey Bacon'])
        if item_ordered == 'Spaghetti Pomodoro with Burrata':
            extras.append(['+ Beef Steak Slices'])
        extras.append(['N/A'])

        reply_keyboard = telegram.ReplyKeyboardMarkup(extras,
                                                      resize_keyboard=True)
        bot.send_chat_action(chat_id=update.effective_user.id,
                             action=telegram.ChatAction.TYPING)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Please write any remarks that you want to add.'
                              ' You can also choose from the options available'
                              ' in the reply keyboard. If you have nothing'
                              ' to add, please select N/A.\r\n\r\n'
                              'NOTE: Do limit your remarks to 700 characters.',
                         reply_markup=reply_keyboard)
        return REMARKS

    # Integer overflow error handling
    except OverflowError:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Your quantity value is too big. '
                              'Please enter a valid value.')


# Function to ask user about time of collection
@operating_time
def time_select(bot, update):
    user_id = update.effective_user.id
    contact_number = int(update.message.text)
    db.add_contact_number(contact_number, user_id)
    time_options = db.time_list()
    reply_keyboard = telegram.ReplyKeyboardMarkup(time_options)
    bot.send_chat_action(chat_id=update.effective_user.id,
                         action=telegram.ChatAction.TYPING)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Before payment, please select a valid time '
                          'of collection for all of your orders.',
                     reply_markup=reply_keyboard)

    return COLLECTION_TIME


# Function to add delivery location (if applicable)
@operating_time
def locator(bot, update):
    time_options = db.time_list()
    time = update.effective_message.text
    user_id = update.effective_user.id
    reply_keyboard = telegram.ReplyKeyboardMarkup(time_options)
    reply_markup = telegram.ReplyKeyboardRemove()
    if [str(time)] not in time_options:
        bot.send_chat_action(chat_id=update.effective_user.id,
                             action=telegram.ChatAction.TYPING)
        bot.send_message(chat_id=update.message.chat_id,
                         text='You have inputted an invalid time. '
                              'Please select a valid time of collection'
                              ' for all of your orders.',
                         reply_markup=reply_keyboard)
    else:
        db.add_time(time, user_id)
        bot.send_chat_action(chat_id=update.effective_user.id,
                             action=telegram.ChatAction.TYPING)
        bot.send_message(chat_id=update.message.chat_id,
                         text='You have selected {} as your time of '
                              'collection.'
                         .format(time), reply_markup=reply_markup)
        location_list = [['Temasek Life Labs'], ['BIZ 2'],
                         ['Innovation Building'], ['Apec Building'],
                         ['N/A']]
        reply_keyboard = telegram.ReplyKeyboardMarkup(location_list,
                                                      resize_keyboard=True)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Please indicate your location for delivery '
                              'purposes. Do take note that delivery is only '
                              'available for the NUS Business School campus '
                              'area.',
                         reply_markup=reply_keyboard)

        return LOCATION


# Function to end /order ConversationHandler
@operating_time
def end_order(bot, update):
    remarks = str(update.message.text)
    user_id = update.effective_user.id

    if user_id in SUPER_ADMIN:
        remarks = remarks + ' (P.S. Bot speaking here. Please treat this guy' \
                            ' nicely as he is literally my creator. Thank ' \
                            'you!)'
    elif user_id in ADMIN_LIST:
        remarks = remarks + ' (P.S. Bot speaking here. Please treat this ' \
                            'person nicely as he/she is literally your boss.' \
                            ' Thank you!)'

    item_ordered = str(db.select_latest_item(user_id))[2:-2]
    db.add_remarks(remarks, user_id, item_ordered)
    latest_item_quantity = str(db.select_latest_quantity(user_id))[1:-1]
    print(str(datetime.now()) + ' - User {} ordered {}x {}.'
          .format(user_id, latest_item_quantity, item_ordered))
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_message(chat_id=update.message.chat_id,
                     text='Your order has been received. You can either add '
                          'more items, check your cart, proceed to payment or '
                          'cancel your order. Do take note that only '
                          'orders with successful payment will be '
                          'considered.',
                     reply_markup=reply_markup)

    return ConversationHandler.END


def fallback(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text='Please complete your previous order first.')


# Function for checking the user's current cart
@operating_time
def cart(bot, update):
    user_id = update.effective_user.id
    item_list = db.check_order(user_id)
    total_price = Decimal('{}'.format(str(sum(item_list[2])))).__round__(2)

    try:
        cart_list = '\r\n'.join(['• ' + str(item_list[0][i]) + ' x' +
                                 str(int(item_list[1][i])) + ' - $' + str(
            Decimal('{}'.format(str(item_list[2][i]))).__round__(2))
                                 for i in range(len(item_list[0]))])
        if not item_list[0]:
            bot.send_message(chat_id=update.message.chat_id,
                             text='Your cart is currently empty. '
                                  'Please order an item first.')
        else:
            bot.send_chat_action(chat_id=update.effective_user.id,
                                 action=telegram.ChatAction.TYPING)
            bot.send_message(parse_mode='HTML', chat_id=update.message.chat_id,
                             text='Currently, these items are in your '
                                  'cart:\r\n\r\n{}\r\n\r\n'
                                  'Total payable: <b>${}</b>'
                             .format(str(cart_list), str(total_price)))

    # Handling error if no quantity is inputted
    except TypeError:
        bot.send_message(chat_id=update.message.chat_id,
                         text='You have not entered any valid quantity '
                              'value for the item that you have ordered.')


# Function to cancel the order
# TODO: Make this not cancel current orders when cancelling /editmenu
def cancel(bot, update):
    user_id = update.effective_user.id
    item_list = db.check_order(user_id)
    reply_markup = telegram.ReplyKeyboardRemove()
    if not item_list[0]:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Your cart is currently empty. '
                              'Please order an item first.',
                         reply_markup=reply_markup)
    else:
        db.delete_order(user_id)
        print(str(datetime.now()) + ' - User {} cancelled his/her '
                                    'order.'.format(user_id))
        bot.send_message(chat_id=update.message.chat_id,
                         text='Your order has been cancelled.\r\n\r\n'
                              'NOTE: Only your orders with pending payment '
                              'status are cancelled.',
                         reply_markup=reply_markup)

    return ConversationHandler.END


@operating_time
def offers(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text='Currently, there are no offers available. '
                          'Stay tuned!')
    # offer_list = [db.check_offer()]
    # bot.send_message(chat_id=update.message.chat_id,
    #                  text='These offers are active currently: {}'
    #                  .format(str(offer_list).strip('[]'))


@operating_time
def fullname_entry(bot, update):
    user_id = update.effective_user.id
    item_list = db.check_order(user_id)
    reply_markup = telegram.ReplyKeyboardRemove()
    if not item_list[0]:
        bot.send_chat_action(chat_id=update.effective_user.id,
                             action=telegram.ChatAction.TYPING)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Your cart is currently empty. Please '
                              'order an item first.',
                         reply_markup=reply_markup)

        return ConversationHandler.END

    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Before payment, we need to collect your '
                              'details for contact purposes.\r\n\r\n'
                              'Please enter your full name.')

        return FULL_NAME


@operating_time
def contact_number_entry(bot, update):
    full_name = str(update.message.text)
    user_id = update.effective_user.id
    db.add_full_name(full_name, user_id)
    reply_markup = telegram.ReplyKeyboardRemove()
    bot.send_chat_action(chat_id=update.effective_user.id,
                         action=telegram.ChatAction.TYPING)
    bot.send_message(chat_id=update.message.chat_id,
                     text='Please input your 8-digit Singapore-based contact '
                          'number.',
                     reply_markup=reply_markup)

    return CONTACT_NUMBER


@operating_time
def start_payment(bot, update):
    location = str(update.message.text)
    user_id = update.effective_user.id
    chat_id = update.effective_message.chat_id
    db.add_location(location, user_id)
    # Price in dollars
    total_price = Decimal('{}'.format(str(sum(db.check_order(user_id)[2])))).__round__(2)
    item_list = db.check_order(user_id)

    cart_list = '\r\n'.join(['• ' + str(item_list[0][i]) + ' x' +
                             str(int(item_list[1][i])) + ' - $' +
                             str(Decimal('{}'.format(str(item_list[2][i]))).__round__(2))
                             for i in range(len(item_list[0]))])
    if not item_list[0]:
        bot.send_message(chat_id=chat_id,
                         text='Your cart is currently empty. '
                              'Please order an item first.')

        return ConversationHandler.END

    else:
        reply_markup = telegram.ReplyKeyboardRemove()
        bot.send_chat_action(chat_id=chat_id,
                             action=telegram.ChatAction.TYPING)
        bot.send_message(parse_mode='HTML', chat_id=chat_id,
                         text='<b>The Spread Bot - Payment Invoice</b>'
                              '\r\n\r\n{}\r\n\r\n'
                              'Total Payable: <b>${}</b>\r\n\r\n'
                              'Please pay using the following '
                              'dynamically-generated QR Code. '
                              'You may use PayLah for payment method.'
                         .format(str(cart_list), str(total_price)),
                         reply_markup=reply_markup)
        # TODO: Implement dynamic QR Code generation function here and send to user
        bot.send_photo(chat_id=chat_id, photo=open('./images/qr_code.JPG', 'rb'))
        bot.send_message(chat_id=chat_id,
                         text='After payment, please take a screenshot '
                              'of your receipt/successful payment page '
                              'and send the image here for verification '
                              'purposes.\r\n\r\n'
                              'NOTE: Please send a legitimate image (not as '
                              'a file). Failure to comply will lead to your '
                              'order being nullified without any '
                              'compensations.')

        return RECEIPT_IMAGE


# Add receipt screenshot to database and end transaction
@operating_time
def end_payment(bot, update):
    receipt_image = bot.get_file(update.message.photo[-1].file_id)['file_path']
    response = requests.get(receipt_image)
    user_id = update.effective_user.id
    db.add_receipt_image(response.content, user_id)
    db.paid_payment_status(user_id)
    print(str(datetime.now()) + ' - User {} has paid for their order.'.format(user_id))
    bot.send_message(chat_id=update.message.chat_id,
                     text='Thank you for your payment! Please show your '
                          'proof of transaction to the waiter at The Spread '
                          'as proof to collect your order. After collecting '
                          'your order, please allow the waiter to delete the '
                          'screenshot. Have a nice day ahead and enjoy your '
                          'meal!\r\n\r\nWARNING: Do not delete the image '
                          'yourself before collecting your order, as it will'
                          ' render your order invalid!')

    return ConversationHandler.END


def main():
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler for /order command
    order_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(quantity)],

        states={
            QUANTITY: [MessageHandler(Filters.regex('^[0-9]+$'),
                                      remarks)],

            REMARKS: [MessageHandler(Filters.text and Filters.regex('^.{1,700}$'), end_order)]

        },

        fallbacks=[CommandHandler('cancel', cancel),
                   CommandHandler('order', fallback),
                   CommandHandler('start', fallback),
                   CommandHandler('help', fallback),
                   CommandHandler('menu', fallback),
                   CommandHandler('terms', fallback),
                   CommandHandler('offers', fallback),
                   CommandHandler('cart', fallback),
                   CommandHandler('pay', fallback),
                   CommandHandler('purge', fallback),
                   CommandHandler('vieworderlist', fallback),
                   CommandHandler('editmenu', fallback),
                   CommandHandler('deletepaiduser', fallback),
                   CommandHandler('root', fallback)],

        per_message=False,

        allow_reentry=False
    )

    payment_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('pay', fullname_entry)],

        states={

            FULL_NAME: [MessageHandler(Filters.text, contact_number_entry)],

            CONTACT_NUMBER: [MessageHandler(Filters.regex('^[0-9]{8}$'),
                                            time_select)],

            COLLECTION_TIME: [MessageHandler(Filters.regex('[0-2][0-9]'':'
                                                           '[0134][05]'),
                                             locator)],

            LOCATION: [MessageHandler(Filters.regex('^Temasek Life Labs$') |
                                      Filters.regex('^BIZ 2$') |
                                      Filters.regex('^Innovation Building$') |
                                      Filters.regex('^Apec Building$'),
                                      start_payment)],

            RECEIPT_IMAGE: [MessageHandler(Filters.photo, end_payment)]
        },

        fallbacks=[CommandHandler('cancel', cancel),
                   CommandHandler('order', fallback),
                   CommandHandler('start', fallback),
                   CommandHandler('help', fallback),
                   CommandHandler('menu', fallback),
                   CommandHandler('terms', fallback),
                   CommandHandler('offers', fallback),
                   CommandHandler('cart', fallback),
                   CommandHandler('pay', fallback),
                   CommandHandler('purge', fallback),
                   CommandHandler('vieworderlist', fallback),
                   CommandHandler('editmenu', fallback),
                   CommandHandler('deletepaiduser', fallback),
                   CommandHandler('root', fallback)],

        per_message=False,

        allow_reentry=False
    )

    editmenu_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('editmenu', editmenu)],

        states={
            EDIT_MENU: [MessageHandler(Filters.photo, menu_editor)]
        },

        fallbacks=[CommandHandler('cancel', cancel),
                   CommandHandler('order', fallback),
                   CommandHandler('start', fallback),
                   CommandHandler('help', fallback),
                   CommandHandler('menu', fallback),
                   CommandHandler('terms', fallback),
                   CommandHandler('offers', fallback),
                   CommandHandler('cart', fallback),
                   CommandHandler('pay', fallback),
                   CommandHandler('purge', fallback),
                   CommandHandler('vieworderlist', fallback),
                   CommandHandler('editmenu', fallback),
                   CommandHandler('deletepaiduser', fallback),
                   CommandHandler('root', fallback)],

        per_message=False,

        allow_reentry=False
    )

    dp.add_handler(order_conv_handler)
    dp.add_handler(payment_conv_handler)
    dp.add_handler(editmenu_conv_handler)

    # Simple start function
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', start))
    dp.add_handler(CommandHandler('menu', menu))
    dp.add_handler(CommandHandler('terms', terms))
    dp.add_handler(CommandHandler('offers', offers))
    dp.add_handler(CommandHandler('order', order))
    dp.add_handler(CommandHandler('cart', cart))
    dp.add_handler(CommandHandler('cancel', cancel))
    # This command will not be in the list of commands
    dp.add_handler(CommandHandler('purge', purge))
    # This command will not be in the list of commands
    dp.add_handler(CommandHandler('vieworderlist', vieworderlist))
    # This command will not be in the list of commands
    dp.add_handler(CommandHandler('deletepaiduser', delete_paid, pass_args=True))
    # This command will not be in the list of commands
    dp.add_handler(CommandHandler('root', root))

    dp.add_handler(MessageHandler(Filters.text, food_category), group=0)

    # Setup database
    db.setup()

    # Log all errors
    dp.add_error_handler(error)

    # Start the bot
    # updater.start_polling(timeout=0)

    updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=BOT_TOKEN)
    updater.bot.set_webhook(WEBHOOK_URL + BOT_TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
