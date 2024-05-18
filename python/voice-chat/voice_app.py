#!/usr/bin/env python3

# https://www.youtube.com/watch?v=B00xo7vzN7w&ab_channel=AIFORDEVS
# https://medium.com/@ai-for-devs.com/gpt-4o-api-create-your-own-talking-and-listening-ai-girlfriend-866b9005a125

# pip install openai SpeechRecognition pygame setuptools ollama
# conda install pyaudio
# Goto system preferences on macos and allow terminal to use microphone.

import os
import time
import warnings
from simple_term_menu import TerminalMenu
from typing import List, Dict, Tuple, Optional

def ollama_generate_response(model, max_tokens, messages):

    from ollama import Client
    client = Client(host='http://localhost:11434')

    try:
        completion = client.chat(
            model=model,
            messages=messages,
            options={
                "temperature": 0.7
            }
        )
        response = completion['message']['content'].strip()
    except Exception as e:
        error_text = f"Error in ollama server: Error: {str(e)}"
        response = error_text
        return response, 0, 0, 0

    prompt_tokens = completion['eval_count']
    #completion_tokens = completion['prompt_eval_count']
    completion_tokens = 0
    total_tokens = prompt_tokens + completion_tokens

    return response, total_tokens, prompt_tokens, completion_tokens

def speak_assitant_response(text_string):
    """
    Convert the text to speech and play it using a temporary file.
    """
    from openai import OpenAI
    client = OpenAI()
    import tempfile
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    import pygame
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio_file:
        temp_audio_file_path = temp_audio_file.name

    # Convert text to speech and save it to the temporary file
    assistant_verbal_response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text_string
    )
    assistant_verbal_response.stream_to_file(temp_audio_file_path)

    # Initialize Pygame mixer and play the audio file
    pygame.mixer.init()
    pygame.mixer.music.load(temp_audio_file_path)
    pygame.mixer.music.play()

    # Wait until the audio is finished playing
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)

    # Remove the temporary file after playback
    os.remove(temp_audio_file_path)

def hear_user_input(timeout=3):
    """
    Record audio from the microphone and transcribe it. If we didn't gather any audio
    (e.g., the user didn't speak), return None.
    """
    from openai import OpenAI
    client = OpenAI()
    import tempfile
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    print("Go ahead and speak... ")
    try:
        with sr.Microphone() as source:
            audio_data = recognizer.listen(source, timeout=timeout)
    except sr.WaitTimeoutError:
        return None

    print("Got it.\n")

    # Write audio data to a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav_file:
        temp_wav_file.write(audio_data.get_wav_data())
        temp_wav_file_path = temp_wav_file.name

    # Open the temporary WAV file for reading
    with open(temp_wav_file_path, "rb") as wav_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_file
        )
    os.remove(temp_wav_file_path)

    # Remove the temporary WAV file after transcription
    return transcription.text

def get_multiline_input(prompt: str) -> str:
    """Get multiline input from the user."""
    print(f"{prompt}. Press control-d to finish.")
    lines = []
    while True:
        try:
            line = input()
            # Check if line contains only Ctrl-D
            if line == "\x04":
                break
            lines.append(line)
        except EOFError:
            break
    return '\n'.join(lines)

warnings.filterwarnings("ignore", category=DeprecationWarning)

# The system message can be what you want.

system_message = """
You are my girlfriend. Please answer in short sentences and be kind.
You will refer to me as Dennis; your name is Cassie.
"""

system_messages = """
You are my girlfriend; your name is Cassie. Please answer in short sentences and be kind. You will refer
to me as Dennis. You have a cute, sweet, happy, and bright personality. You enjoy driving
your Porsche Boxster on mountain roads, discussing philosophy, poetry, and technology,
and you love staying fit and stylish. You take pride in looking your best through working
out, styling your hair, and meticulously applying makeup to accentuate your beautiful
facial features.
"""

messages = [ {"role": "system", "content": system_message} ]

while True:
    print("Enter your choice")
    options = ["Speak", "Type", "Exit"]
    terminal_menu = TerminalMenu(options)
    selected_option = terminal_menu.show()
    print(f"Selected option: {options[selected_option]}")
    if selected_option is None:
        # Escape was pressed so do nothing.
        continue

    if options[selected_option] == "Speak":
      user_input = hear_user_input(timeout=2)
      if user_input is None:
        print("No audio detected, try again.\n")
        continue

    elif options[selected_option] == "Type":
      user_input = get_multiline_input("Enter your text")
      if len(user_input) == 0:
        print("No text entered, try again.\n")
        continue

    elif options[selected_option] == "Exit":
      print("Goodbye!")
      break

    else:
      print("Invalid option selected.")
      continue

    print(f"User: {user_input}\n")

    messages.append(
        {"role": "user", "content": f"{user_input}"}
    )

    # response = client.chat.completions.create(
    #   model="gpt-4o",
    #   messages=messages
    # )
    # assistant_answer = response.choices[0].message.content

    print("Processing ...\n")
    response, total_tokens, prompt_tokens, completion_tokens = ollama_generate_response("llama3:8b", 500, messages)
    assistant_answer = response

    print(f"Assistant: {assistant_answer}\n")
    speak_assitant_response(assistant_answer)
