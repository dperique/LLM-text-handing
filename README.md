# LLM text handling

These are programs that handle text using LLMs.  We try hard to use quality opensource (free) LLMs first and also paid models where appropriate.

Before running any of the programs, do this:

```bash
python -m env venv
source ./env/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)/python
```

Setup an [ollama service](https://github.com/ollama/ollama/blob/ba04afc9a45a095e09e72c1d716fdfe941d9b340/docs/linux.md#adding-ollama-as-a-startup-service-recommended) or get an openai apikey.

## Text summarizer

Taking inspiration from [infiniteGPT](https://github.com/emmethalm/infiniteGPT) and other chunking methods (e.g., llama-index), we have a text summarizer that can use ollama or openai.  Use ollama for private summarization,
hence the name `osummarize`

Run it like this:

```bash
./python osummarize/osummarize.py
```

## Streamlit text summarizer

Using [streamlit](streamlit.io), we have a summarizer that can be used via a web interface as a "co-pilot" for your text summarization needs.

Run it like this:

```bash
streamlit run --server.port 8509 --server.headless True --theme.base dark sl_summarize/sl_osummary.py
```

Then browse to [localhost:8509](localhost:8509).  You can create multiple tabs with that link so you can have
multiple summarizations.

## HTML reader

This is an app that can read webpages.  It is quite rudimentary but useful for gathering text from webpages (e.g., for summarization).

Run it like this:

```bash
python/reader/reader.py
```

## Voice conversation chat

Taking inspiration from [this youtube video](https://www.youtube.com/watch?v=B00xo7vzN7w&ab_channel=AIFORDEVS) showing chatgpt4o with whisper and tts-1 model, we make a simple, chat application using a popular chat application coding pattern.  The program makes use of the ollama api and openai tts-1 model.

NOTE: `pip install pyaudio` did not work for me but `conda install pyaudio` did.

Run it like this:

```bash
export OPENAI_API_KEY=sk-... (fill in your API key)
python/voice-chat/voice-chat.py
```