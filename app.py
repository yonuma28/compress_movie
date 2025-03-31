import os
import time
import asyncio
import requests
import threading
import cloudinary
import cloudinary.uploader
from flask import Flask, request, render_template, jsonify
import discord
from discord import Intents
from threading import Thread

# 環境変数の読み込み
TOKEN = os.getenv('TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 1343840413420617748))
CLOUD_NAME = os.getenv('CLOUD_NAME')
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# Cloudinary の設定
cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET
)

# Discord クライアント設定
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Flask アプリケーション設定
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/keep_alive', methods=['GET'])
def keep_alive():
    return jsonify({'message': 'Alive'}), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    """動画を受け取り、Cloudinary にアップロードし、Discord に送信"""
    if 'file' not in request.files:
        return 'ファイルが見つかりませんでした。', 400
    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が空です。', 400
    
    title = request.form.get('title', 'Video')
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    threading.Thread(target=process_and_upload, args=(file_path, title)).start()
    return render_template('upload.html', message='ファイルがアップロードされました！')

@app.route('/send_video', methods=['POST'])
def send_video():
    """Discord に動画の URL を送信"""
    data = request.json
    video_url = data.get('video_url')
    title = data.get('title', 'Video')
    
    if video_url:
        channel = client.get_channel(CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            message = f"[{title}]({video_url})"
            asyncio.run_coroutine_threadsafe(channel.send(message), client.loop)
        return jsonify({'message': '動画 URL を Discord に送信しました'}), 200
    return jsonify({'message': '動画 URL が見つかりませんでした'}), 400

def process_and_upload(file_path, title):
    """Cloudinary に動画をアップロードし、Discord に送信"""
    upload_result = cloudinary.uploader.upload(
        file_path, resource_type='video', eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
    )
    video_url = upload_result['secure_url']
    print(f"Uploaded: {video_url}")
    
    try:
        response = requests.post('https://compress-movie.onrender.com/send_video', json={"video_url": video_url, "title": title})
        print(f"Sent video URL to Discord: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending video URL: {e}")

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ping_replit():
    """指定されたURLに60秒おきにリクエストを送る"""
    while True:
        try:
            response = requests.get("https://2c6aa011-4aab-4719-a328-72141802bf19-00-1sun3j2fbtgrc.riker.replit.dev/keep_alive")
            logger.info(f"Ping to keep_alive: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error sending ping: {e}")
        logger.info("実行")
        time.sleep(60)

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # ping_replit関数を別スレッドで実行
    ping_thread = Thread(target=ping_replit, daemon=True)
    ping_thread.start()
    
    client.run(TOKEN)
