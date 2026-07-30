import telebot
import yt_dlp
import os
import time
from telebot import types

TOKEN = '8687331632:AAGVslikcenwq7wXPm9fSenKZ_gVnOy4Ppo'
bot = telebot.TeleBot(TOKEN)

CHANNEL_ID = "@K05_050" 
search_mode = {}

def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        print(f"⚠️ Ошибка проверки подписки (сеть): {e}")
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_search = types.KeyboardButton("🔍 Поиск музыки")
        markup.add(btn_search)
        
        bot.reply_to(
            message, 
            "Привет! Отправь мне ссылку на видео/музыку ИЛИ нажми кнопку «🔍 Поиск музыки», чтобы найти трек по названию 🎧.", 
            reply_markup=markup
        )
    except Exception as e:
        print(f"Ошибка в /start: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.from_user.id
        text = message.text
        chat_id = message.chat.id
        
        # 🔒 Проверка подписки с защитой от сбоев
        if not check_sub(user_id):
            markup = types.InlineKeyboardMarkup()
            btn_channel = types.InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/K05_050")
            btn_check = types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub_yes")
            markup.add(btn_channel, btn_check)
            
            bot.send_message(
                chat_id, 
                "⚠️ Чтобы пользоваться ботом, подпишись на наш канал!", 
                reply_markup=markup
            )
            return

        if text == "🔍 Поиск музыки":
            search_mode[user_id] = True
            bot.send_message(chat_id, "✍️ Напиши название песни или исполнителя, которого хочешь найти:")
            return

        if search_mode.get(user_id):
            search_mode[user_id] = False
            search_and_send_results(chat_id, text)
            return

        if text.startswith('http://') or text.startswith('https://'):
            download_and_send_link(chat_id, text, message.message_id)
        else:
            bot.reply_to(message, "Используй кнопку «🔍 Поиск музыки» или отправь ссылку на скачивание!")
            
    except Exception as e:
        print(f"⚠️ Ошибка при обработке сообщения: {e}")

# 🔍 Поиск треков с защитой try-except
def search_and_send_results(chat_id, query):
    status_msg = bot.send_message(chat_id, f"🔍 Ищу треки: «{query}»...")
    search_query = f"ytsearch5:{query}"
    
    ydl_opts = {
        'quiet': True,
        'nocheckcertificate': True,
        'extract_flat': True,
        'skip_download': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            entries = result.get('entries', [])
            
        if not entries:
            bot.edit_message_text(f"❌ По запросу «{query}» ничего не найдено.", chat_id, status_msg.message_id)
            return

        markup = types.InlineKeyboardMarkup()
        for item in entries:
            title = item.get('title', 'Трек')
            video_id = item.get('id')
            if not video_id:
                continue
                
            if len(title) > 40:
                title = title[:37] + "..."
            
            btn = types.InlineKeyboardButton(f"🎵 {title}", callback_data=f"dl_{video_id}")
            markup.add(btn)

        bot.edit_message_text(
            "🎧 Вот что удалось найти, выбери нужную песню:", 
            chat_id, 
            status_msg.message_id, 
            reply_markup=markup
        )
        
    except Exception as e:
        bot.edit_message_text("❌ Ошибка при поиске (проблемы с сетью). Попробуй еще раз.", chat_id, status_msg.message_id)
        print(f"Ошибка поиска в yt_dlp: {e}")

# Скачивание и отправка с полным отловом ошибок
def download_and_send_link(chat_id, url, msg_id):
    filename_template = f'media_{chat_id}_{msg_id}.%(ext)s'
    status_msg = bot.send_message(chat_id, "⚙️ Скачиваю музыку...")

    audio_file = None

    try:
        ydl_audio_opts = {
            'outtmpl': filename_template,
            'format': 'bestaudio',
            'quiet': True,
            'nocheckcertificate': True
        }
        with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
            info_audio = ydl.extract_info(url, download=True)
            audio_file = ydl.prepare_filename(info_audio)

        if audio_file and os.path.exists(audio_file):
            with open(audio_file, 'rb') as aud:
                bot.send_audio(chat_id, aud, caption="🎧 Твой трек")

        bot.delete_message(chat_id, status_msg.message_id)
        
    except Exception as e:
        bot.send_message(chat_id, "❌ Не удалось скачать файл. Проверь ссылку или попробуй другую.")
        print(f"Ошибка загрузки: {e}")
        
    finally:
        # Гарантированно чистим файлы, даже если произошел сбой
        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def callback_download_search(call):
    try:
        video_id = call.data.replace('dl_', '')
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        bot.answer_callback_query(call.id, "Загружаю выбранный трек! 🚀")
        bot.edit_message_text("⚙️ Скачиваю песню...", call.message.chat.id, call.message.message_id)
        
        download_and_send_link(call.message.chat.id, url, call.message.message_id)
    except Exception as e:
        print(f"Ошибка в обработчике кнопок: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub_yes")
def callback_sub_check(call):
    try:
        user_id = call.from_user.id
        if check_sub(user_id):
            bot.answer_callback_query(call.id, "Подписка подтверждена! 🎉")
            bot.send_message(call.message.chat.id, "Отлично! Теперь пользуйся ботом.")
        else:
            bot.answer_callback_query(call.id, "Ты еще не подписался на канал!", show_alert=True)
    except Exception as e:
        print(f"Ошибка проверки подписки по кнопке: {e}")

# 🛡️ Бессмертный запуск бота с автовосстановлением связи при обрывах
if __name__ == '__main__':
    print("Бот запущен в защищенном режиме...")
    while True:
        try:
            # none_stop=True держит соединение, а таймауты не дают боту падать наглухо
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"⚠️ Произошел обрыв соединения или сбой сети: {e}")
            print("🔄 Пробую переподключиться через 5 секунд...")
            time.sleep(5)