#!pip install pyTelegramBotAPI SpeechRecognition pydub gTTS Pillow requests
#!pip install pyTelegramBotAPI SpeechRecognition
#две верхних библиотеки запускаем в среде выполнения (console)
import telebot
import speech_recognition
from pydub import AudioSegment
from PIL import Image, ImageEnhance, ImageFilter
import requests
import json
from gtts import gTTS # Added for text-to-speech
import textwrap
import os

API_KEY = "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" # внутри скобок свой апи ключ отсюда https://openrouter.ai/settings/keys
MODEL = "openai/gpt-oss-20b:free"

def process_content(content):
    return content.replace('<think>', '').replace('</think>', '')

def chat_stream(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }

    with requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        stream=True
    ) as response:
        if response.status_code != 200:
            print("Ошибка API:", response.status_code)
            return ""

        full_response = []

        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode('utf-8').replace('data: ', '')
                try:
                    chunk_json = json.loads(chunk_str)
                    if "choices" in chunk_json:
                        content = chunk_json["choices"][0]["delta"].get("content", "")
                        if content:
                            cleaned = process_content(content)
                            print(cleaned, end='', flush=True)
                            full_response.append(cleaned)
                except:
                    pass

        print()  # Перенос строки после завершения потока
        #return ''.join(full_response)
        full_response_text = ''.join(full_response)
        full_response_text1 = full_response_text.replace('*''#', ' ')
        return textwrap.shorten(full_response_text1, width=800, placeholder="...")


# ↓↓↓ Ниже нужно вставить токен, который дал BotFather при регистрации
# Пример: token = '2007628239:AAEF4ZVqLiRKG7j49EC4vaRwXjJ6DN6xng8'
token = '7200178392:AAE7zLwOBGSlUjsEwBhywb0h2GQqEiJ4ldg'  # <<< Ваш токен

bot = telebot.TeleBot(token)


def transform_image(filename):
    # Функция обработки изображения
    source_image = Image.open(filename)
    enhanced_image = source_image.filter(ImageFilter.BoxBlur(8.0))
    enhanced_image = enhanced_image.convert('RGB')
    width = enhanced_image.size[0]
    height = enhanced_image.size[1]

    enhanced_image = enhanced_image.resize((width // 2, height // 2))

    enhanced_image.save(filename)
    return filename


@bot.message_handler(content_types=['photo'])
def resend_photo(message):
    # Функция отправки обработанного изображения
    file_id = message.photo[-1].file_id
    filename = download_file(bot, file_id)

    # Трансформируем изображение
    transform_image(filename)

    image = open(filename, 'rb')
    bot.send_photo(message.chat.id, image)
    image.close()

    # Не забываем удалять ненужные изображения
    if os.path.exists(filename):
        os.remove(filename)


def oga2wav(filename):
    # Конвертация формата файлов
    new_filename = filename.replace('.oga', '.wav')
    audio = AudioSegment.from_file(filename)
    audio.export(new_filename, format='wav')
    return new_filename


def recognize_speech(oga_filename):
    # Перевод голоса в текст + удаление использованных файлов
    wav_filename = oga2wav(oga_filename)
    recognizer = speech_recognition.Recognizer()

    with speech_recognition.WavFile(wav_filename) as source:
        wav_audio = recognizer.record(source)

    text = recognizer.recognize_google(wav_audio, language='ru')

    if os.path.exists(oga_filename):
        os.remove(oga_filename)

    if os.path.exists(wav_filename):
        os.remove(wav_filename)

    return text


def download_file(bot, file_id):
    # Скачивание файла, который прислал пользователь
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    filename = file_id + file_info.file_path
    filename = filename.replace('/', '_')
    with open(filename, 'wb') as f:
        f.write(downloaded_file)
    return filename


@bot.message_handler(commands=['start'])
def say_hi(message):
    # Функция, отправляющая "Привет" в ответ на команду /start
    bot.send_message(message.chat.id, 'Привет спроси меня о чём-либо или напиши')


@bot.message_handler(content_types=['voice'])
def transcript(message):
    # Функция, отправляющая текст в ответ на голосовое
    filename = download_file(bot, message.voice.file_id)
    text = recognize_speech(filename)
    mess = chat_stream(text)
    send_audio_from_text(message.chat.id, mess) # Call the new helper function
    bot.send_message(message.chat.id, mess)


def send_audio_from_text(chat_id, text):
    if not text:
        return

    try:
        tts = gTTS(text=text, lang='ru')
        audio_file = 'output.mp3'
        tts.save(audio_file)

        audio = open(audio_file, 'rb')
        bot.send_voice(chat_id, audio)
        audio.close()
        os.remove(audio_file)
    except Exception as e:
        bot.send_message(chat_id, f'Произошла ошибка при озвучивании: {e}')

@bot.message_handler(content_types=['text'])
def text_message_handler(message):
    send_audio_from_text(message.chat.id, message.text)

bot.polling()
