#!/usr/bin/env python3

# streamlit run --server.port 8509 --server.headless True --theme.base dark sl_osummary.py

import os
import requests
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
import pyperclip
from typing import Any, List, Tuple, Optional

from utils.chat_utils import call_ollama_api, fixup_line, timestamp_pattern, youtube_timestamp_pattern, highlight_regex_matches, process_chunks, load_text

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

# Track the chunksize and overlap values so that we can be dynamic since
# text sizes change and we want to give the user reasonable defaults if
# we can figure them out for them.
initial_chunk_size: int = 500
initial_overlap_size: int = 50

if 'chunk_size_value' not in st.session_state:
    st.session_state['chunk_size_value'] = initial_chunk_size

if 'overlap_size_value' not in st.session_state:
    st.session_state['overlap_value'] = initial_overlap_size

with st.sidebar:
    st.title("Summary Co-Pilot")
    input_type: str | None = st.radio("Select input type:", ("File", "Clipboard", "Scrape URL to clipboard"))

    # We want to set text according to the input type
    text: str = ""

    if input_type == "File":
        uploaded_file: UploadedFile|None = st.file_uploader(f"Choose a file", key='file_uploader')
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
        clipboard_text: str = pyperclip.paste()
        text = clipboard_text
        st.session_state['text'] = [text]
        st.session_state['page_start'] = None
        st.session_state['page_end'] = None
        st.session_state['word_size'] = len(clipboard_text.split(' '))

    elif input_type == "Scrape URL to clipboard":
        # Checkbox to choose whether to prepend Jina.ai URL
        # Scrape the url with or without jina and just render it as markdown
        # and also, add it to the clipboard so we can summarize.
        use_jina: bool = st.checkbox("Use jina.ai URL", value=True)
        url: str = st.text_input("Enter URL to scrape:")
        if url:
            if use_jina:
                full_url: str = "https://r.jina.ai/" + url
                headers: dict = {"Authorization": os.getenv("JINA_API_KEY")}
            else:
                full_url = url
                headers = {}
            try:
                response = requests.get(full_url, headers=headers)
                response.raise_for_status()
                scraped_text = response.text
                pyperclip.copy(scraped_text)
                st.session_state['text'] = [scraped_text]
                st.session_state['page_start'] = None
                st.session_state['page_end'] = None
                st.session_state['word_size'] = len(scraped_text.split(' '))

                # Add the scraped text so it can be saved (not tested)
                st.session_state['summary'] = scraped_text
                text = scraped_text
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching the URL: {e}")

    if st.session_state['word_size'] < st.session_state['chunk_size_value']:
        # If the clipboard text is less than the chunk size, shrink the chunk and overlap
        # values that make more sense.
        st.session_state['chunk_size_value'] = st.session_state['word_size']
        st.session_state['overlap_value'] = int(st.session_state['chunk_size_value'] * .20)
    else:
        # Reset the chunk and overlap values to the initial values if
        # the clipboard text changes to something larger.
        st.session_state['chunk_size_value'] = initial_chunk_size
        st.session_state['overlap_value'] = initial_overlap_size
    st.text(f"Word Size: {st.session_state['word_size']}")

    #chunk_size_min = min(st.session_state['word_size'], 100)
    #chunk_size_max = max(st.session_state['word_size'], 1000)
    chunk_size: int = st.slider("Chunk Size", min_value=0, max_value=1000, value=st.session_state['chunk_size_value'])

    overlap: int = st.slider("Overlap", min_value=0, max_value=chunk_size-1, value=st.session_state['overlap_value'])

    # Search dialog for regex pattern
    regex_pattern: str = st.sidebar.text_input("Enter regex pattern to highlight")

    if st.button("Generate Summary"):
        if st.session_state['text']:
            st.session_state['summary'] = "Processing..."
            if input_type == "File" and uploaded_file is not None and uploaded_file.name.endswith('.pdf'):
                page_start: int = st.session_state['page_start']
                page_end: int = st.session_state['page_end']
                selected_pages_text: str = ' '.join(st.session_state['text'][page_start-1:page_end])
                st.session_state['summary'] = process_chunks(selected_pages_text, chunk_size, overlap)
            else:
                st.session_state['summary'] = process_chunks(' '.join(st.session_state['text']), chunk_size, overlap)
        else:
            st.error("Please provide text to summarize.")

    save_summary: str = st.text_input("Save summary as (filename):")
    if st.button("Save Summary", disabled=not st.session_state['summary']):
        if save_summary:
            with open(save_summary, "w") as file:
                file.write(st.session_state['summary'])
            st.success(f"Summary saved to {save_summary}")
        else:
            st.error("Please provide a filename to save the summary.")

tmp_start: Optional[int] = st.session_state['page_start']
tmp_end: Optional[int] = st.session_state['page_end']
tmp_display: str = f"{tmp_start} - {tmp_end}"
if tmp_end is None:
    tmp_display = ""
tmp_display += f" ({st.session_state['word_size']} words)"

st.markdown(f"#### Summary: {tmp_display} chunkSize={chunk_size}/Overlap={overlap}")

if regex_pattern:
    highlighted_summary: str = highlight_regex_matches(st.session_state['summary'], regex_pattern)
    st.markdown(highlighted_summary, unsafe_allow_html=True)
else:
    st.markdown(st.session_state['summary'])
