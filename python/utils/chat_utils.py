import re
import os
import json
from typing import List, Dict, Tuple, Optional

# Constants
SUMMARY_PROMPT = """
You are a summarization machine. I will give you text, you will summarize the text as
a list of bullet points where each bullet point identifies any important points.
The output should be in the form of a json array of maps with single key/value pairs
where for each bullet the key is always "key"; the beginning and ending brackets should
be on separate lines. For example, the output will look like:

[
{"key": "<the bullet point>"}
{"key": "<the bullet point>"}
]
The key and bullet point should always be on a single line.
"""
timestamp_pattern = r'\[(\d{2}:)?\d{2}:\d{2}\.\d{3} --> (\d{2}:)?\d{2}:\d{2}\.\d{3}\]'

# The youtube transcript timestamps look like (27:16) or (1:27:16)
youtube_timestamp_pattern = r'\((\d{1,2}:)?\d{2}:\d{2}\)'


# Function to load text from a file or pdf
# Returns a list of strings (text) and the number of pages (num_pages)
def load_text(file, page_start=None, page_end=None):
    import PyPDF2
    try:
        if file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(file)
            pages_text = []
            num_pages = len(pdf_reader.pages)
            if page_start is None:
                page_start = 1
            if page_end is None or page_end > num_pages:
                page_end = num_pages
            for page_num in range(page_start - 1, page_end):
                page = pdf_reader.pages[page_num]
                pages_text.append(page.extract_text())
            return pages_text, num_pages

        return [file.read().decode('utf-8')], None
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None, None

# Function to split text into chunks
def split_into_chunks(text, chunk_size, overlap):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        chunks.append(' '.join(chunk))
        start = end - overlap

    if len(chunks) > 1 and len(chunks[-1].split()) < overlap:
        chunks[-2] += ' ' + chunks[-1]
        chunks.pop()
    return chunks

# Function to process chunks and generate summaries
def process_chunks(text, chunk_size, overlap):
    chunks = split_into_chunks(text, chunk_size, overlap)
    responses = []

    for chunk in chunks:
        raw_response = call_ollama_api(chunk, SUMMARY_PROMPT)

        tmp_response = []

        # If this chunk has a timestamp on it (e.g., like a whisper timestamp),
        # let's print it to help guide the user to the original text.
        match = re.search(timestamp_pattern, chunk)
        if match:
            tmp_response.append(match.group())

        # If this chunk has a youtube timestamp on it, let's print it to help
        # guide the user to the original text.
        match = re.search(youtube_timestamp_pattern, chunk)
        if match:
            tmp_response.append(match.group())

        errors_found = 0
        for line in raw_response.split('\n'):
            if '"key":' in line:

                line = fixup_line(line)

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # If we can't parse the line as JSON, just append it as is
                    # to avoid losing data; we'll strip the key part to make it
                    # look like an almost legitimate bullet point.
                    bullet_point = '* ' + line.split('"key":')[1].strip()
                    tmp_response.append(bullet_point)
                    errors_found += 1
                    continue
                bullet_point = '* ' + data['key']
                tmp_response.append(bullet_point)

        print(f"Errors found: {errors_found}")
        responses.append('\n'.join(tmp_response))
        responses.append("\n***")

    return '\n\n'.join(responses)

# Function to fix up lines for JSON parsing
def fixup_line(line):
    line = re.sub(r'\{\s*\{+', '{', line)
    line = re.sub(r'\}\s*\}+', '}', line)
    line = line.replace('""}]', '"}')
    line = line.replace('}]', '}')
    line = line.replace('},', '')
    if not line.startswith('{'):
        line = '{' + line
    if not line.endswith('}'):
        line = line + '}'
    line = line.replace('""}', '"}')
    line = line.replace('}, }', '}')
    if line.endswith(']'):
        line = line[:-1]
    line = line.replace('"} }', '"}')
    return line

# Function to highlight regex matches in text
def highlight_regex_matches(text, pattern):
    highlighted_text = re.sub(pattern, r'<mark style="background-color: yellow;">\g<0></mark>', text, flags=re.IGNORECASE)
    return highlighted_text

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
    (e.g., the user didn't speak), return "".
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
        return ""

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

def call_openai_api(chunk, summary_prompt) -> str:
    return "DO NOT USE YET!"
    messages = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": f"{chunk}."},
    ]

    response, total_tokens, prompt_tokens, completion_tokens = openai_generate_response(
        model="gpt-3.5-turbo",
        max_tokens=500,
        messages=messages
    )
    # We only return the message content to match the original function's return type
    return response.strip()

def call_ollama_api(chunk, summary_prompt) -> str:
    messages = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": f"{chunk}."},
    ]

    response, total_tokens, prompt_tokens, completion_tokens = ollama_generate_response(
        model="llama3:8b",
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

def openai_generate_response(model: str, max_tokens: int, messages: List[Dict[str, str]]) -> Tuple[str, int, int, int]:
    return "DO NOT USE YET!", 0, 0, 0
    """
    Generate a response from the Openai API using the specified model and messages.
    """
    import openai
    openai.api_key = "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

    try:
        completion = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            n=1,
            stop=None,
            temperature=0.5,
        )
        response = completion.choices[0]['message']['content'].strip()
    except Exception as e:
        error_text = f"Error in OpenAI API: Error: {str(e)}"
        response = error_text
        return response, 0, 0, 0

    return response, completion.total_tokens, completion.prompt_tokens, completion.completion_tokens

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
