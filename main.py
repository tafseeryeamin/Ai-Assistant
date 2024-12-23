import datetime
import os
import sys
import time
import webbrowser
import pyautogui
import pyttsx3
import speech_recognition as sr
import json
import pickle
import requests  # Added missing import
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import random
import numpy as np
import psutil
import subprocess

# Load model and data
try:
    with open("intents.json") as file:
        data = json.load(file)

    model = load_model("chat_model.h5")

    with open("tokenizer.pkl", "rb") as f:
        tokenizer = pickle.load(f)

    with open("label_encoder.pkl", "rb") as encoder_file:
        label_encoder = pickle.load(encoder_file)
except FileNotFoundError as e:
    print(f"File not found: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error loading AI components: {e}")
    sys.exit(1)

# Initialize text-to-speech engine
def initialize_engine():
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'female' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.setProperty('rate', engine.getProperty('rate') - 50)
        engine.setProperty('volume', min(engine.getProperty('volume') + 0.25, 1.0))
        return engine
    except Exception as e:
        print(f"TTS Engine Error: {e}")
        return None

engine = initialize_engine()
# Load model and data
with open("intents.json") as file:
    data = json.load(file)

model = load_model("chat_model.h5")

with open("tokenizer.pkl", "rb") as f:
    tokenizer = pickle.load(f)

with open("label_encoder.pkl", "rb") as encoder_file:
    label_encoder = pickle.load(encoder_file)

WEATHER_API_KEY = "4f59de6ccda449d9880143938242312"

def get_weather(city="Kawagoe"):
    try:
        response = requests.get(f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&aqi=no")
        weather_data = response.json()
        condition = weather_data['current']['condition']['text']
        temp_c = weather_data['current']['temp_c']
        return f"The current weather in {city} is {condition} with a temperature of {temp_c}°C."
    except Exception as e:
        return "Sorry, I couldn't fetch the weather details."

def speak(text):
    if engine:
        engine.say(text)
        engine.runAndWait()
    else:
        print("TTS engine not initialized.")

def command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        recognizer.pause_threshold = 1.0
        try:
            audio = recognizer.listen(source, timeout=5)
            query = recognizer.recognize_google(audio, language='en-in')
            print(f"User said: {query}")
            return query.lower()
        except sr.UnknownValueError:
            print("Sorry, I didn't catch that.")
        except sr.RequestError:
            print("Speech recognition service is unavailable.")
        return ""

def cal_day():
    day_dict = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday",
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    return day_dict.get(datetime.datetime.today().weekday(), "Unknown")

def wishMe():
    hour = int(datetime.datetime.now().hour)
    t = time.strftime("%I:%M %p")
    day = cal_day()
    weather = get_weather()
    if 0 <= hour < 12:
        speak(f"Good morning, it's {day} and the time is {t}. {weather}")
    elif 12 <= hour < 16:
        speak(f"Good afternoon, it's {day} and the time is {t}. {weather}")
    else:
        speak(f"Good evening, it's {day} and the time is {t}. {weather}")

def browsing(query):
    if 'google' in query:
        speak("What would you like to search for on Google?")
        search_query = command()
        if search_query:
            webbrowser.open(f"https://www.google.com/search?q={search_query}")

def handle_sites(query):
    sites = {
        "youtube": "https://www.youtube.com",
        "wikipedia": "https://www.wikipedia.com",
        "google": "https://www.google.com",
        "facebook": "https://www.facebook.com",
        "github": "https://www.github.com",
        "linkedin": "https://www.linkedin.com",
        "collab": "https://colab.research.google.com"
    }
    for site, url in sites.items():
        if f"open {site}" in query:
            speak(f"Opening {site}")
            webbrowser.open(url)
            return

def handle_series(query):
    series = {
        "friends": "https://noxx.to/tv/friends/"
    }
    for serie, url in series.items():
        if f"i want to see {serie}" in query or f"open {serie}" in query:
            speak(f"Opening {serie}, enjoy!")
            webbrowser.open(url)
            return


def handle_volume(query):
    if "volume up" in query:
        os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 10)'")
        speak("Volume increased")
    elif "volume down" in query:
        os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 10)'")
        speak("Volume decreased")
    elif "volume mute" in query:
        os.system("osascript -e 'set volume with output muted'")
        speak("Volume muted")

def process_general_query(query):
    padded_sequences = pad_sequences(tokenizer.texts_to_sequences([query]), maxlen=20, truncating='post')
    result = model.predict(padded_sequences)
    tag = label_encoder.inverse_transform([np.argmax(result)])[0]

    for intent in data['intents']:
        if intent['tag'] == tag:
            response = random.choice(intent['responses'])
            speak(response)
            return
    speak("I'm not sure how to respond to that.")
import wikipedia  # Add this import

# Add this function after your existing functions
def get_wiki_info(query):
    try:
        topic = query.split("know about")[1].strip()
        wiki_summary = wikipedia.summary(topic, sentences=2)
        return wiki_summary
    except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError, Exception) as e:
        speak(f"No Wikipedia entry found for {topic}. Let me search Google for you.")
        webbrowser.open(f"https://www.google.com/search?q={topic}")
        return f"I've opened Google search results for {topic}."
if __name__ == "__main__":
    speak("Welcome, I am Lana. Developed by Tafseer Sir. How can I assist you today?")
    wishMe()

    while True:
        query = command()
        if not query:
            continue
        if "weather" in query:
            city = "Tokyo"
            speak("Which city would you like the weather for?")
            city_query = command()
            if city_query:
                city = city_query
            weather_info = get_weather(city)
            speak(weather_info)
        if "know about" in query:
            info = get_wiki_info(query)
            speak(info)
        if "lana sleep now" in query:
            speak("Goodbye! Have a nice day!")
            sys.exit()
        handle_sites(query)
        handle_series(query)
        handle_volume(query)
        if any(keyword in query for keyword in ["what", "who", "how", "hi", "thanks", "hello"]):
            process_general_query(query)
        elif "open google" in query:
            browsing(query)
