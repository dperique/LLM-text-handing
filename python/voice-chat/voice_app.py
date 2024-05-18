#!/usr/bin/env python3

# https://www.youtube.com/watch?v=B00xo7vzN7w&ab_channel=AIFORDEVS
# https://medium.com/@ai-for-devs.com/gpt-4o-api-create-your-own-talking-and-listening-ai-girlfriend-866b9005a125

# pip install openai SpeechRecognition pygame setuptools ollama
# conda install pyaudio
# Goto system preferences on macos and allow terminal to use microphone.

import warnings
from simple_term_menu import TerminalMenu
from chat_utils import hear_user_input, speak_assitant_response, ollama_generate_response, get_multiline_input

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
