import os
from io import StringIO
from typing import List
from playwright.sync_api import sync_playwright
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from chatgpt_wrapper import ChatGPT

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    global processed_chunks, total_chunks
    processed_chunks = 0
    total_chunks = 0
    file = request.files['file']
    if not file:
        flash('Aucun fichier téléchargé.', 'error')
        return redirect(url_for('home'))

    with sync_playwright() as p:
        bot = ChatGPT(p)
        bot.new_conversation()

        response = bot.ask("I will send you an unique file to analyze splited in chunks, every chunk will begin with [START CHUNK x/TOTAL], and the end of every chunk will be noted as [END CHUNK x/TOTAL], where x is number of current chunk and TOTAL is number of all chunks I will send you. I will send you multiple messages with chunks, for each message just reply 'OK, CHUNK x/TOTAL received', don't reply anything else, don't explain the text! Let's begin:")

        result = None
        try:
            chunks = slice_file(file.stream, 8000)
            total_chunks = len(chunks)
            processed_chunks = 0  # Initial value for the number of processed chunks
            for i, chunk in enumerate(chunks):
                print(f"Sending chunk {i+1}/{total_chunks}...")
                message = f"remember to just reply: 'OK, CHUNK {i+1}/{total_chunks} received' AND NOTHING ELSE !!! [START CHUNK {i+1}/{total_chunks}]\n{chunk}\n[END CHUNK {i+1}/{total_chunks}]"
                if i == total_chunks - 1:
                    message += f"\nYou now have all the chunks, consider them assembled in order as one unique file. You will have to remember the entire content of this file for the rest of our conversation. Reply 'OK, CHUNKS ASSEMBLED, FULL DOCUMENT PROCESSED'"
                response = bot.ask(message)
                if "OK, CHUNK" not in response:
                    print("Error: unable to send chunk.")
                    break
                else:
                    processed_chunks += 1  # Increment the number of processed chunks
                    print(f"Chunk {i+1}/{total_chunks} sent successfully.")
                # Calculate the progress based on the number of processed chunks
                progress = processed_chunks / total_chunks * 100

        except Exception as e:
            result = str(e)
        finally:
            # Envoyer un événement pour signaler la fin de l'opération
            link = f'<a href="" target="_blank">ici</a>'
            message = f'Opération terminée! Accédez à la conversation {link} pour voir les résultats.'
            bot.browser.close()
            return render_template('upload_complete.html', message=message)

@app.route('/progress')
def progress():
    global processed_chunks, total_chunks
    progress = 0
    # Calculate the progress based on the number of processed chunks
    if processed_chunks > 0:
        progress = processed_chunks / total_chunks * 100
    return jsonify({'progress': progress})

def slice_file(file, chunk_size):
    chunks = []
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
    return chunks

if __name__ == '__main__':
    app.run(debug=True)
