#!/usr/bin/env python3

import sys
import json
import re
import os
from utils.chat_utils import call_ollama_api

# Return a string of the text from the file.
# Handle pdf files by first extracting the text from the pdf.
def load_text(file_path):
    if file_path.endswith('.pdf'):
        import PyPDF2
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        return text

    with open(file_path, 'r') as file:
        return file.read()

def save_to_file(responses, output_file):
    print(f"Saving responses to {output_file}")
    with open(output_file, 'w') as file:
        for response in responses:
            file.write(response + '\n')

# Clipboard file
CLIPBOARD_FILE = "/tmp/clipboard.txt"

# Regex to match whisper transcripts with timestamps.
timestamp_pattern = r'\[(\d{2}:)?\d{2}:\d{2}\.\d{3} --> (\d{2}:)?\d{2}:\d{2}\.\d{3}\]'

# This prompt works well but you'll need to fixup the output as the LLM is not so
# consistent with producing well formed json.
SUMMARY_PROMPT = """
You are a summarization machine. I will give you text, you will summarize the text as
a list of bullet points where each buullet point identifies any important points.
The output should be in the form of a json array of maps with single key/value pairs
where for each bullet the key is always "key"; the beginning and ending brackets should
be on separate lines.  For example, the output will look like:

[
{"key": "<the bullet point>"}
{"key": "<the bullet point>"}
]
The key and bullet point should always be on a single line.
"""

# Change your OpenAI chat model accordingly

def call_openai_api(chunk):
    # Add your own OpenAI API key

    import openai
    openai.api_key = "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "PASS IN ANY ARBITRARY SYSTEM VALUE TO GIVE THE AI AN IDENITY"},
            {"role": "user", "content": f"YOUR DATA TO PASS IN: {chunk}."},
        ],
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response.choices[0]['message']['content'].strip()

def split_into_chunks(text, chunk_size, overlap):

    print(f"Splitting text into chunks of {chunk_size} tokens with an overlap of {overlap} tokens")
    count = 1
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        print(f"Extracting text chunk {count}")

        # Ensure that we do not go out of index
        end = start + chunk_size
        chunk = words[start:end]
        chunks.append(' '.join(chunk))
        # Move start forward by chunk size minus the overlap
        start = end - overlap
        count = count + 1

    # If the last chunk is less than overlap tokens, merge it with the previous chunk
    # to avoid a dangling last chunk with little context for summarization.
    if len(chunks) > 1 and len(chunks[-1].split()) < overlap:
        chunks[-2] += ' ' + chunks[-1]
        chunks.pop()
    return chunks

DEBUG = False
def debug_print(text):
    if DEBUG:
        print(text)

# This function is used to fix up the line so that it can be parsed by json.loads.
# Unfortunately, LLMs don't always produce proper json even when specifically asked.
def fixup_line(line):

    # Replace multiple opening braces and optional spaces with a single opening brace
    line = re.sub(r'\{\s*\{+', '{', line)

    # Replace multiple closing braces and optional spaces with a single closing brace
    line = re.sub(r'\}\s*\}+', '}', line)

    # If line ends with '""}]' make it end with '"}'.
    if line.endswith('""}]'):
        line = line.replace('""}]', '"}')

    # If line ends with '}]', make it end with '}'.
    if line.endswith('}]'):
        line = line.replace('}]', '}')

    # If the line ends with a '},', remove the comma.
    if line.endswith('},'):
        line = line[:-1]

    # Sometimes the line is not delimted by braces, if so, add them.
    if not line.startswith('{'):
        line = '{' + line
    if not line.endswith('}'):
        line = line + '}'

    # Sometimes a line has two quotes followed by and ending brace, if so,
    # just have one quote followed by the ending brace.
    if '""}' in line:
        line = line.replace('""}', '"}')

    # Sometimes a line ends with '}, }' and we only need one ending brace.
    if '}, }' in line:
        line = line.replace('}, }', '}')

    # Strip off any closing bracket.
    if line.endswith(']'):
        line = line[:-1]

    # Trans for a trailing '"} }' to '"}'
    if '"} }' in line:
        line = line.replace('"} }', '"}')

    return line

# Take a line of the form "* ...", and format it so that it fits within the max_width.
# Any lines exceeding max_width are split into multiple lines. The indentation of the
# line is preserved. The function returns an array of strings where each string is a
# line that fits within the max_width.
def format_line(line, max_width):
    formatted_lines = []
    line = line.strip()

    # Degenerate (single line) case.
    if len(line) <= max_width:
        return [line]

    # Find the position of the first space after "* " to determine the indentation
    first_space_index = line.find(' ') + 1
    indent = ' ' * first_space_index

    # Continue processing the line until its length is manageable
    while len(line) > max_width:
        # Find last space before max_width to avoid splitting words
        break_point = line.rfind(' ', first_space_index, max_width)
        if break_point == -1:  # This handles a long word at the start of the line
            break_point = max_width

        formatted_lines.append(line[:break_point])
        # Remove the part of the line that has been appended and continue
        line = indent + line[break_point:].lstrip()

    # Append any remaining part of the line
    if line:
        formatted_lines.append(line)

    return formatted_lines

# Write a formatted bullet point to the file. The bullet point is a string that starts
# with "* " but is a single line.  Use this function to write the bullet point to the file
# so that it spans a limited width.
def write_formatted_bullet(file, bullet_point, max_width, doFormat):

    if doFormat:
        lines = format_line(bullet_point, max_width)
    else:
        lines = [bullet_point]
    for line in lines:
        file.write(line + '\n')
    file.flush()

# Process chunks of text and summarize each chunk using some LLM model.
# The output is written to the output file.
# The chunk_size is the number of words in each chunk and overlap is the number of words
# that each chunk overlaps with the previous chunk.
def process_chunks(input_file, output_file, chunk_size, overlap, max_width, doFormat):
    text = load_text(input_file)
    chunks = split_into_chunks(text, chunk_size, overlap)

    if output_file == "to_stdout":
        output_object = sys.stdout
    else:
        output_object = open(output_file, 'w')

    with output_object as file:
        count = 1
        total_chunks = len(chunks)
        responses = []
        for chunk in chunks:
            print(f"Summarizing chunk {count} of {total_chunks}", file=sys.stderr)
            debug_print(f"Chunk:\n\n {chunk}\n\n")
            raw_response = call_ollama_api(chunk, SUMMARY_PROMPT)
            debug_print(f"Raw response:\n\n {raw_response}\n\n")

            # If this chunk has a timestamp on it (e.g., like a whisper timestamp),
            # let's print it to help guide the user to the original text.
            match = re.search(timestamp_pattern, chunk)
            if match:
                # Print the matched timestamp
                file.write(match.group() + '\n')

            # Take only the lines in response that start with '"key":', strip any comma
            # that comes after a closing brace, then build an array of strings with
            # each of the values.
            tmp_response = []
            errors_found = 0
            for line in raw_response.split('\n'):
                if '"key":' in line:
                    original_line = line

                    # Fixing up twice helps.
                    line = fixup_line(line)
                    line = fixup_line(line)

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as e:
                        # If we can't parse the line as JSON, just append it as is
                        # to avoid losing data; we'll strip the key part to make it
                        # look like an almost legitimate bullet point.
                        bullet_point = '* ' + line.split('"key":')[1].strip() + "Error: text repaired"
                        tmp_response.append(bullet_point)
                        errors_found += 1

                        # Update the output file so the user to see the summarization as it occurs.
                        write_formatted_bullet(file, bullet_point, max_width, doFormat)
                        continue
                    bullet_point = '* ' + data['key']
                    tmp_response.append(bullet_point)
                    # Update the output file so the user to see the summarization as it occurs.
                    write_formatted_bullet(file, bullet_point, max_width, doFormat)

            # Put a line to delimit chunks.
            file.write('\n')
            if errors_found > 0:
                print(f"  Errors found: {errors_found}")
            processed_response = '\n'.join(tmp_response)
            debug_print(f"Processed response:\n\n{processed_response}\n\n")
            responses.append(processed_response)
            count = count + 1

# Specify your input and output files
if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} <input_file_prefix> <chunk_size> <formatMode> <stdOut>")
        print("\nParameters:")
        print("  <input_file_prefix>  Base name of the input file. The script uses this prefix to")
        print("                       find '<input_file_prefix>.txt' as the input file and")
        print("                       generates '<input_file_prefix>.md' as the output file.")
        print("                       Use 'clipboard' to summarize the contents of the clipboard.")
        print("  <chunk_size>         Number of lines to include in each chunk of the output.")
        print("                       Must be an integer.")
        print("  <formatMode>         Boolean flag ('True' or 'False'). If 'True', the output")
        print("                       will be formatted. If 'False', no formatting will be applied.")
        print("  <stdOut>             Boolean flag ('True' or 'False'). If 'True', the output will")
        print("                       be printed to stdout instead of an output file.")

        print("\nDescription:")
        print("  This script processes chunks of text from a specified input file and outputs")
        print("  them into a markdown file or stdout. Each chunk of text is processed according")
        print("  to the specified 'chunk_size', and optional formatting can be applied.")
        sys.exit(1)

    input_file_prefix = sys.argv[1]
    chunk_size_arg = sys.argv[2]
    doFormat = sys.argv[3]
    stdoutMode = sys.argv[4]

    try:
        chunk_size = int(chunk_size_arg)
    except ValueError as e:
        print(f"The chunk size must be an integer: {str(e)}")
        sys.exit(1)

    if doFormat == "True":
        doFormat = True
    elif doFormat == "False":
        doFormat = False
    else:
        print("formatMode must be either True or False")
        sys.exit(1)

    # extract the root of the filename
    extension = input_file_prefix.split('.')[-1]
    input_file_prefix = input_file_prefix.replace('.' + extension, "")
    print(f"Extension: {extension}")
    if extension == "pdf":
        input_file = sys.argv[1]
    else:
        input_file = input_file_prefix + ".txt"
    if input_file_prefix == "clipboard":
        # Read what's in the clipboard and create a file called /tmp/cliipboard.txt
        # with the clipboard contents.
        import pyperclip
        clipboard_text = pyperclip.paste()
        print(f"Using clipboard mode; see {CLIPBOARD_FILE} for the clipboard contents")
        with open(CLIPBOARD_FILE, "w") as file:
            file.write(clipboard_text)
        input_file = CLIPBOARD_FILE
    output_file = input_file_prefix + ".md"
    if stdoutMode == "True":
        output_file = "to_stdout"
    print(f"Input file: {input_file}; output file: {output_file}")
    print(f"Chunk size: {chunk_size}, overlap: 50, max width: 100, format: {doFormat}")
    process_chunks(input_file, output_file, chunk_size=chunk_size, overlap=50, max_width=100, doFormat=doFormat)
