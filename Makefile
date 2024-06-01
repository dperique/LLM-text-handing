.PHONY: lint

lint:
	mypy python/sl_summarize/sl_osummary.py
	mypy python/reader/reader.py
	mypy python/voice-chat/voice_app.py
	mypy python/osummarize/osummarize.py
