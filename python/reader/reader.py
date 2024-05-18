#!/usr/bin/env python

import sys

# url = "http://paulgraham.com/worked.html"
# url = "https://www.cnbc.com/2024/05/11/sweetgreen-chipotle-and-wingstop-arent-seeing-a-consumer-slowdown.html"
# url = "https://finance.yahoo.com/news/buffett-selling-apple-stock-reason-113300696.html"

# If the user passed in a start_text, look for the first occurrence
# of that text in the document and return the text starting from that.
# The point is to remove all the text before the start_text.
def chopout(text, start_text):
    if len(start_text) >= 0:
        start_index = text.find(start_text)
        if start_index >= 0:
            return text[start_index:]
        else:
            return text
    return text

def url_to_text_simple(url, start_text=""):
    # pip install requests html2text
    import requests
    import html2text
    response = requests.get(url, headers=None).text
    response = html2text.html2text(response)
    return chopout(response, start_text)

def url_to_text(url, start_text=""):
    # pip install llama-index llama-index-readers-web IPython
    # I uninstalled all this because it was just huge.  Since
    # this is no better than the simple mode, I'm not going to
    # use it.
    from llama_index.readers.web import SimpleWebPageReader
    documents = SimpleWebPageReader(html_to_text=True).load_data(urls=[url])
    document_as_dict = documents[0].to_dict()
    return chopout(document_as_dict['text'], start_text)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <URL> <start_text>")
        print("\nParameters:")
        print("  <URL>         The URL of the web page to fetch and process.")
        print("  <start_text>  A string that marks the starting point in the fetched text.")
        print("                The output will include text from this point onwards.")
        print("                Pass in "" if you don't want to specify a starting point.")

        print("\nDescription:")
        print("  This script fetches text from the specified URL using the requests")
        print("  web reader, and optionally starts output from a user-specified text.")
        print("  This is useful for extracting a specific section of a web page.")
        sys.exit(1)
    url = sys.argv[1]
    # url = 'https://tradingbotsreviews.com/new/?utm_source=taboola&utm_medium=referral&tblci=GiDL1ILU0OLMk_szq58lewF03J0cuwaKsB8F_tCoQTleviCdyFsog-rL2KiHiLh2MMQE#tblciGiDL1ILU0OLMk_szq58lewF03J0cuwaKsB8F_tCoQTleviCdyFsog-rL2KiHiLh2MMQE'
    # start_text = ''
    start_text = sys.argv[2]

    # both methods yield identical output
    #print(url_to_text(url, start_text=start_text))
    print(url_to_text_simple(url, start_text=start_text))
    #for key in document_as_dict:
    #    print(key)


