import os
import time
import asyncio
import requests
import threading
import cloudinary
import cloudinary.uploader
from flask import Flask, request, render_template, jsonify, redirect, url_for
import discord
from discord.ext import commands
from threading import Thread

import logging

# ロギングの設定
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


TOKEN = os.getenv('TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 1244248370307010654))

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Cloudinary の設定
cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

# Discord クライアント設定
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/keep_alive', methods=['GET'])
def keep_alive():
    return jsonify({'message': 'Alive'}), 200

@app.route('/send_video', methods=['POST'])
def send_video():
    """受け取った動画を Cloudinary にアップロードし、Discord に送信"""
    data = request.json
    video_file = data.get('file')  # 受け取ったファイル
    title = data.get('title', 'Video')

    logger.info("ここまでは行けている")
    if video_file:
        file_path = f"uploads/{video_file.filename}"
        video_file.save(file_path)

        upload_result = cloudinary.uploader.upload(
            file_path, resource_type='video', eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
        )
        video_url = upload_result['secure_url']

        channel = bot.get_channel(CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            asyncio.run_coroutine_threadsafe(channel.send(f"[{title}]({video_url})"), bot.loop)
        return jsonify({'message': '動画 URL を Discord に送信しました'}), 200

    return jsonify({'message': '動画ファイルが見つかりませんでした'}), 400

@app.route('/upload', methods=['POST'])
def upload_file():
    """動画を受け取り、Cloudinary にアップロードし、Discord に送信"""
    if 'file' not in request.files:
        return 'ファイルが見つかりませんでした。', 400
    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が空です。', 400
    
    title = request.form.get('title', 'Video')
    file_path = f"uploads/{file.filename}"
    file.save(file_path)
    
    threading.Thread(target=process_and_upload, args=(file_path, title)).start()

    # アップロード後に同じページにリダイレクト
    return redirect(url_for('index'))

def process_and_upload(file_path, title):
    """動画をCloudinaryにアップロードし、そのURLをDiscordに送信する"""
    logger.info(f"Starting upload for file: {file_path} with title: {title}")
    
    try:
        # Cloudinaryに動画をアップロード
        logger.info("Uploading video to Cloudinary...")
        upload_result = cloudinary.uploader.upload(
            file_path, resource_type='video', eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
        )
        video_url = upload_result['secure_url']
        logger.info(f"Upload successful. Video URL: {video_url}")

        # 非同期でDiscordに動画URLを送信
        async def send_to_discord():
            logger.info(f"Sending video URL to Discord channel: {CHANNEL_ID}")
            channel = bot.get_channel(CHANNEL_ID)
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"[{title}]({video_url})")
            else:
                logger.error(f"Invalid channel: {CHANNEL_ID}")

        # イベントループを使用して非同期タスクを実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_to_discord())
        loop.close()

        logger.info("Video URL sent to Discord successfully.")
    except Exception as e:
        logger.error(f"Error during video upload and Discord send: {e}")


def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

if __name__ == '__main__':
    # Flask を別スレッドで起動
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Discord BOT を非同期で実行
    asyncio.run(bot.start(TOKEN))
