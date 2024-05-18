#!/usr/bin/env python3

# https://www.youtube.com/watch?v=B00xo7vzN7w&ab_channel=AIFORDEVS
# https://medium.com/@ai-for-devs.com/gpt-4o-api-create-your-own-talking-and-listening-ai-girlfriend-866b9005a125

# pip install openai SpeechRecognition pygame setuptools ollama
# conda install pyaudio
# Goto system preferences on macos and allow terminal to use microphone.

import speech_recognition as sr
import pygame
import time
import warnings

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

def record_audio(file_path, timeout=3):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Please say something...")
        audio_data = recognizer.listen(source, timeout=timeout)
        print("Recording complete.")
        with open(file_path, "wb") as audio_file:
            audio_file.write(audio_data.get_wav_data())

def play_audio(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    # Wait until the audio is finished playing
    while pygame.mixer.music.get_busy():
        time.sleep(1)

from openai import OpenAI

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Required for using the whisper tts-1 model (and costs money so monitor your usage)
client = OpenAI()

# The system message can be what you want.

system_message = """
You are my girlfriend. Please answer in short sentences and be kind.
You will refer to me as Dennis; your name is Cassie.
"""

system_messages = """
You are my girlfriend, Cassie. Please answer in short sentences and be kind. You will refer
to me as Dennis. You have a cute, sweet, happy, and bright personality. You enjoy driving
your Porsche Boxster on mountain roads, discussing philosophy, poetry, and technology,
and you love staying fit and stylish. You take pride in looking your best through working
out, styling your hair, and meticulously applying makeup to accentuate your beautiful
facial features.
"""

messages = [ {"role": "system", "content": system_message} ]

tmp_input_audio_file = 'tmp_input.wav'
tmp_output_audio_file = 'tmp_output.mp3'

while True:
  print("Press ENTER to speak or type 'exit' to quit.")
  user_input = input()
  if user_input == "exit":
    break

  record_audio(tmp_input_audio_file, timeout=3)
  audio_file= open(tmp_input_audio_file, "rb")
  transcription = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file
  )

  print(f"{transcription.text}\n\n")

  messages.append(
      {"role": "user", "content": f"{transcription.text}"}
  )

  # response = client.chat.completions.create(
  #   model="gpt-4o",
  #   messages=messages
  # )
  # assistant_answer = response.choices[0].message.content

  response, total_tokens, prompt_tokens, completion_tokens = ollama_generate_response("llama3:8b", 500, messages)
  assistant_answer = response

  print(f"{assistant_answer}\n\n")

  assistant_verbal_response = client.audio.speech.create(
    model="tts-1",
    voice="nova",
    input=assistant_answer
  )

  assistant_verbal_response.stream_to_file(tmp_output_audio_file)
  play_audio(tmp_output_audio_file)
