#!/usr/bin/env python3

# streamlit run --server.port 8509 --server.headless True --theme.base dark sl_osummary.py

import streamlit as st
import pyperclip
import PyPDF2
import os
import json
import re
from utils.chat_utils import call_ollama_api

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

        tmp_response = []
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
                    bullet_point = '* ' + line.split('"key":')[1].strip() + "Error: text repaired"
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

# Streamlit UI
st.set_page_config(page_title="Summary Co-Pilot", layout="wide")

if 'summary' not in st.session_state:
    st.session_state['summary'] = ""

if 'num_pages' not in st.session_state:
    st.session_state['num_pages'] = None

if 'text' not in st.session_state:
    st.session_state['text'] = []

if 'page_start' not in st.session_state:
    st.session_state['page_start'] = 1

if 'page_end' not in st.session_state:
    st.session_state['page_end'] = None

if 'word_size' not in st.session_state:
    st.session_state['word_size'] = 0

with st.sidebar:
    st.title("Summary Co-Pilot")
    input_type = st.radio("Select input type:", ("File", "Clipboard"))

    if input_type == "File":
        uploaded_file = st.file_uploader(f"Choose a file", key='file_uploader')
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.pdf'):
                pages_text, num_pages = load_text(uploaded_file)
                st.session_state['text'] = pages_text
                st.session_state['num_pages'] = num_pages
                if st.session_state['page_end'] is None or st.session_state['page_end'] > num_pages:
                    st.session_state['page_end'] = num_pages
                if num_pages is not None:
                    st.session_state['page_start'] = st.sidebar.number_input("Page Start", min_value=1, max_value=num_pages, value=st.session_state['page_start'], key='page_start_num')
                    st.session_state['page_end'] = st.sidebar.number_input("Page End", min_value=1, max_value=num_pages, value=st.session_state['page_end'], key='page_end_num')
                # Find the number of words in the list of strings (pages_text)
                st.session_state['word_size'] = sum([len(page.split(' ')) for page in pages_text])
            else:
                text, _ = load_text(uploaded_file)
                st.session_state['text'] = text
                st.session_state['word_size'] = sum([len(page.split(' ')) for page in text])
    elif input_type == "Clipboard":
        clipboard_text = pyperclip.paste()
        text = clipboard_text
        st.session_state['text'] = [text]
        st.session_state['page_start'] = None
        st.session_state['page_end'] = None
        st.session_state['word_size'] = len(text.split(' '))

    st.text(f"Word Size: {st.session_state['word_size']}")
    chunk_size = st.slider("Chunk Size", min_value=100, max_value=1000, value=500)
    overlap = st.slider("Overlap", min_value=0, max_value=chunk_size-1, value=50)

    # Search dialog for regex pattern
    regex_pattern = st.sidebar.text_input("Enter regex pattern to highlight")

    if st.button("Generate Summary"):
        if st.session_state['text']:
            st.session_state['summary'] = "Processing..."
            if input_type == "File" and uploaded_file.name.endswith('.pdf'):
                page_start = st.session_state['page_start']
                page_end = st.session_state['page_end']
                selected_pages_text = ' '.join(st.session_state['text'][page_start-1:page_end])
                st.session_state['summary'] = process_chunks(selected_pages_text, chunk_size, overlap)
            else:
                st.session_state['summary'] = process_chunks(' '.join(st.session_state['text']), chunk_size, overlap)
        else:
            st.error("Please provide text to summarize.")

    save_summary = st.text_input("Save summary as (filename):")
    if st.button("Save Summary", disabled=not st.session_state['summary']):
        if save_summary:
            with open(save_summary, "w") as file:
                file.write(st.session_state['summary'])
            st.success(f"Summary saved to {save_summary}")
        else:
            st.error("Please provide a filename to save the summary.")

tmp_start = st.session_state['page_start']
tmp_end = st.session_state['page_end']
tmp_display = f"{tmp_start} - {tmp_end}"
if tmp_end is None:
    tmp_display = ""
tmp_display += f" ({st.session_state['word_size']} words)"

st.markdown(f"#### Summary: {tmp_display} chunkSize={chunk_size}/Overlap={overlap}")

if regex_pattern:
    highlighted_summary = highlight_regex_matches(st.session_state['summary'], regex_pattern)
    st.markdown(highlighted_summary, unsafe_allow_html=True)
else:
    st.markdown(st.session_state['summary'])
