from typing import List, Dict, Tuple, Optional

def speak_assitant_response(text_input: str) -> None:
    """
    Convert the text to speech and play it using a temporary file.
    Assumes OPENAI_API_KEY is set in the environment.
    """
    import os
    import time
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
        input=text_input
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

def hear_user_input(timeout: int = 3) -> str:
    """
    Record audio from the microphone and transcribe it. If we didn't gather any audio
    (e.g., the user didn't speak), return None.
    Assumes OPENAI_API_KEY is set in the environment.
    """
    import os
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

def call_ollama_api(model, chunk, summary_prompt):
    messages = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": f"{chunk}."},
    ]

    response, total_tokens, prompt_tokens, completion_tokens = ollama_generate_response(
        model=model,
        max_tokens=500,
        messages=messages
    )
    # We only return the message content to match the original function's return type
    return response.strip()

def ollama_generate_response(model: str, max_tokens: int, messages: List[Dict[str, str]]) -> Tuple[str, int, int, int]:
    """
    Generate a response from the Ollama API using the specified model and messages.
    This requires that the Ollama server is running and available at 127.0.0.1:11434.
    """
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

def get_multiline_input(prompt: str) -> List[str]:
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
