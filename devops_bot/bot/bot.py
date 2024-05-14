import logging
import re, os, paramiko
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from dotenv import load_dotenv
import psycopg2
import subprocess

#load_dotenv()

host = os.getenv('RM_HOST')
port = os.getenv('RM_PORT')
username = os.getenv('RM_USER')
password = os.getenv('RM_PASSWORD')


cur_host = os.getenv('CURRENT_HOST')
cur_port = os.getenv('CURRENT_PORT')
cur_username = os.getenv('CURRENT_USER')
cur_password = os.getenv('CURRENT_PASSWORD')


db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_username = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_db = os.getenv('DB_DATABASE')


TOKEN = os.getenv("TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'findPhoneNumbers'


def findPhoneNumbers (update: Update, context):
    user_input = update.message.text 

    phoneNumRegex = re.compile(r'(\+7|8)(\s\d{3}\s\d{3}\s\d{2}\s\d{2}|-\d{3}-\d{3}-\d{2}-\d{2}|\(\d{3}\)\d{3}\d{2}\d{2}|\s\(\d{3}\s\d{3}\s\d{2}\s\d{2}|\d{10})') 

    phoneNumberList = phoneNumRegex.findall(user_input) 

    if not phoneNumberList: 
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END 
    logging.info("Список телефонных номеров" + str(phoneNumberList))
    phoneNumbers = '' 
    for i in range(len(phoneNumberList)):
        #phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n' # Записываем очередной номер
        phoneNumber = phoneNumberList[i][0] + phoneNumberList[i][1]
        phoneNumbers += f'{i+1}. {phoneNumber}\n'
        
    update.message.reply_text(phoneNumbers) 
    update.message.reply_text('Вы хотите записать найденную информацию в БД?\nНапишите \'да\',если хотите, \'нет\' в противном случае')
    context.user_data['phoneNumberList'] = phoneNumberList
    return 'saveToBase'


def helpCommand(update: Update, context):
    update.message.reply_text('Help!')


def findEmailsCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска email-адресов: ')

    return 'findEmails'


def findEmails (update: Update, context):
    user_input = update.message.text 

    emailRegex = re.compile(r'[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+') 

    emailList = emailRegex.findall(user_input) 

    if not emailList:
        update.message.reply_text('Email-адреса не найдены')
        return ConversationHandler.END 
    
    logging.info("Список email-адресов" + str(emailList))

    emails = ''
    for i in range(len(emailList)):
        emails += f'{i+1}. {emailList[i]}\n'
        
    update.message.reply_text(emails) 
    update.message.reply_text('Вы хотите записать найденную информацию в БД?\nНапишите \'да\',если хотите, \'нет\' в противном случае')
    context.user_data['emailList'] = emailList
    return 'saveToBase'


def checkPassCommand(update: Update, context):
    update.message.reply_text('Введите пароль: ')

    return 'checkPassword'


def checkPassword (update: Update, context):
    user_input = update.message.text 

    passRegex = re.compile(r'(?=.*[0-9])(?=.*[!@#$%^&*()])(?=.*[a-z])(?=.*[A-Z])[0-9a-zA-Z!@#$%^&*()]{8,}') 

    symbList = passRegex.findall(user_input) 
    logging.info("Введенный пароль:" + str(symbList))
    if not symbList:
        update.message.reply_text('Пароль простой')
        return ConversationHandler.END 
        
    update.message.reply_text('Пароль сложный') 
    return ConversationHandler.END 


def ExecuteCommand(command, host_, username_, password_, port_):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(str(host))
        client.connect(hostname=host_, username=username_, password=password_, port=port_)
        stdin, stdout, stderr = client.exec_command(command)
        data = stdout.read() + stderr.read()
        client.close()
        data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
        logging.info(data)
        return data
    except:
        return ""
    

def ExecutePostgresCommand(command):
    connection = None
    try:
        connection = psycopg2.connect(user=db_username,
                                    password=db_password,
                                    host=db_host,
                                    port=db_port, 
                                    database=db_db)

        cursor = connection.cursor()
        cursor.execute(command)
        if not "SELECT" in command: connection.commit()
        data = cursor.fetchall()
        logging.info("Команда успешно выполнена")
        return data
    except (Exception, psycopg2.Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            logging.info("Соединение с PostgreSQL закрыто")



def getReleaseCommand(update: Update, context):
    data = ExecuteCommand('lsb_release -a', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getUnameCommand(update: Update, context):
    data = ExecuteCommand('uname -a', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getUptimeCommand(update: Update, context):
    data = ExecuteCommand('uptime', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getDfCommand(update: Update, context):
    data = ExecuteCommand('df -h', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getFreeCommand(update: Update, context):
    data = ExecuteCommand('free -h', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")
    

def getMpstatCommand(update: Update, context):
    data = ExecuteCommand('mpstat -P ALL', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getWCommand(update: Update, context):
    data = ExecuteCommand('w', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getAuthCommand(update: Update, context):
    data = ExecuteCommand('last -n 10', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getCriticalCommand(update: Update, context):
    data = ExecuteCommand('journalctl -p crit -n 5', host, username, password, port)
    #data = ExecuteCommand('cat /var/log/syslog | grep level=error | head -n 5')
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getPsCommand(update: Update, context):
    data = ExecuteCommand('ps aux | head -n 20', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getSsCommand(update: Update, context):
    data = ExecuteCommand('ss | head -n 20', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def getServicesCommand(update: Update, context):
    data = ExecuteCommand('systemctl list-units --type=service --state=active | head -n 20', host, username, password, port)
    if(data != ""): update.message.reply_text(data)
    else: update.message.reply_text("Что-то пошло не так")


def aptListCommand(update: Update, context):
    update.message.reply_text('Введите название пакета, информацию о котором необходимо найти или apt_list, чтобы вывести информацию обо всех установленных пакетах: ')
    return 'aptList'


def aptList(update: Update, context):
    user_input = update.message.text 
    data = ""
    if(user_input == "apt_list"):
        data = ExecuteCommand('apt list --installed | head -n 20', host, username, password, port) 
    else:
        user_input = re.split('[ |&;]', user_input)[0]
        data = ExecuteCommand(f'apt show {user_input}', host, username, password, port)
    
    if(data == ""): 
        update.message.reply_text('Что-то пошло не так')
        return ConversationHandler.END 
    
    update.message.reply_text(data)
    logging.info(user_input)
    logging.info(data)
    return ConversationHandler.END 


def getReplLogsCommand(update: Update, context):
    # data = ExecuteCommand('docker logs ' + db_host, cur_host, cur_username, cur_password, cur_port)
    log_file_path = '/var/log/postgresql/logs.log'
    logging.info("It's right execution")
    data = ""
    with open(log_file_path, 'r') as log_file:
        data = log_file.read()
    if(data != ""): 
        data = reversed(data.splitlines())
        result = ""
        i = 0
        for line in data:
            if('replication' in line or "STATEMENT" in line):
                result += (line + "\n")
                i += 1
            if(i > 20): break
        update.message.reply_text(result)
    else: update.message.reply_text("Что-то пошло не так")



def getEmailsCommand(update: Update, context):
    data = ExecutePostgresCommand("SELECT * FROM Emails;")
    if(data != ""): 
        emails = ''
        for element in data:
            emails += f'{element[0]}. {element[1]}\n'
        update.message.reply_text(emails)
    else: update.message.reply_text("Что-то пошло не так")


def getPhoneNumbersCommand(update: Update, context):
    data = ExecutePostgresCommand("SELECT * FROM PhoneNumbers;")
    if(data != ""):
        numbers = ''
        for element in data:
            numbers += f'{element[0]}. {element[1]}\n'
        update.message.reply_text(numbers)
    else: 
        update.message.reply_text("Что-то пошло не так")


def saveToBase(update: Update, context, data: str, data_type: str):
    user_input = update.message.text 
    if(user_input == "нет"):
        update.message.reply_text('Хорошо')
        return ConversationHandler.END 
    result = ""
    if data_type.lower() == 'phone_numbers':
        for element in data:
            number = element[0] + element[1]
            result = ExecutePostgresCommand(f"INSERT INTO PhoneNumbers (phone_number) VALUES ('{number}');")
    elif data_type.lower() == 'emails':
        for element in data:
            result = ExecutePostgresCommand(f"INSERT INTO Emails (email) VALUES ('{element}');")
    else: update.message.reply_text(f'Что-то пошло не так')

    if(result == ""): update.message.reply_text(f'Что-то пошло не так')
    else: update.message.reply_text(f'Информация {data_type} успешно записана в базу данных.')
    return ConversationHandler.END


def main():

    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'saveToBase': [MessageHandler(Filters.text & ~Filters.command, lambda update, context: saveToBase(update, context, context.user_data['phoneNumberList'], 'phone_numbers'))]
        },
        fallbacks=[]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailsCommand)],
        states={
            'findEmails': [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            'saveToBase': [MessageHandler(Filters.text & ~Filters.command, lambda update, context: saveToBase(update, context, context.user_data['emailList'], 'emails'))]
        },
        fallbacks=[]
    )

    convHandlerСheckPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', checkPassCommand)],
        states={
            'checkPassword': [MessageHandler(Filters.text & ~Filters.command, checkPassword)],
        },
        fallbacks=[]
    )

    convHandlerAptList = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', aptListCommand)],
        states={
            'aptList': [MessageHandler(Filters.text & ~Filters.command, aptList)],
        },
        fallbacks=[]
    )
		
    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(convHandlerFindPhoneNumbers)

    dp.add_handler(convHandlerFindEmails)

    dp.add_handler(convHandlerСheckPassword)

    dp.add_handler(convHandlerAptList)

    dp.add_handler(CommandHandler("help", helpCommand))

    dp.add_handler(CommandHandler("get_release", getReleaseCommand))
    
    dp.add_handler(CommandHandler("get_uname",getUnameCommand))

    dp.add_handler(CommandHandler("get_df",getDfCommand))

    dp.add_handler(CommandHandler("get_uptime",getUptimeCommand))

    dp.add_handler(CommandHandler("get_free",getFreeCommand))

    dp.add_handler(CommandHandler("get_mpstat",getMpstatCommand))

    dp.add_handler(CommandHandler("get_w",getWCommand))

    dp.add_handler(CommandHandler("get_auths",getAuthCommand))

    dp.add_handler(CommandHandler("get_critical",getCriticalCommand))

    dp.add_handler(CommandHandler("get_ps",getPsCommand))

    dp.add_handler(CommandHandler("get_ss",getSsCommand))

    dp.add_handler(CommandHandler("get_services",getServicesCommand))

    dp.add_handler(CommandHandler("get_repl_logs",getReplLogsCommand))

    dp.add_handler(CommandHandler("get_emails",getEmailsCommand))

    dp.add_handler(CommandHandler("get_phone_numbers",getPhoneNumbersCommand))
		
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
