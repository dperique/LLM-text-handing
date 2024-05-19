#!/usr/bin/env python3

# streamlit run --server.port 8509 --server.headless True --theme.base dark sl_osummary.py

import os
import requests
import streamlit as st
import pyperclip

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

with st.sidebar:
    st.title("Summary Co-Pilot")
    input_type = st.radio("Select input type:", ("File", "Clipboard", "Scrape URL to clipboard"))

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

    elif input_type == "Scrape URL to clipboard":

        # Checkbox to choose whether to prepend Jina.ai URL
        use_jina = st.checkbox("Use jina.ai URL", value=True)

        # Scrape the url with or without jina and just render it as markdown
        # and also, add it to the clipboard so we can summarize.
        url = st.text_input("Enter URL to scrape:")
        if url:
            if use_jina:
                full_url = "https://r.jina.ai/" + url
                headers = { "Authorization": os.getenv("JINA_API_KEY") }
            else:
                full_url = url
                headers = {}
            try:
                response = requests.get(full_url, headers=headers)
                response.raise_for_status()
                text = response.text
                pyperclip.copy(text)
                st.session_state['text'] = [text]
                st.session_state['page_start'] = None
                st.session_state['page_end'] = None
                st.session_state['word_size'] = len(text.split(' '))
                st.session_state['summary'] = text
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching the URL: {e}")

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
