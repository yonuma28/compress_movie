import os
import time
import asyncio
import requests
import threading
import cloudinary
import cloudinary.uploader
from flask import Flask, request, render_template, jsonify
import discord
from discord.ext import commands
from threading import Thread

TOKEN = os.getenv('TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 1244248370307010654))

app = Flask(__name__)

# Discord クライアント設定
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@app.route('/keep_alive', methods=['GET'])
def keep_alive():
    return jsonify({'message': 'Alive'}), 200

@app.route('/send_video', methods=['POST'])
def send_video():
    data = request.json
    video_url = data.get('video_url')
    title = data.get('title', 'Video')
    
    if video_url:
        channel = bot.get_channel(CHANNEL_ID)
        if isinstance(channel, discord.TextChannel):
            asyncio.run_coroutine_threadsafe(channel.send(f"[{title}]({video_url})"), bot.loop)
        return jsonify({'message': '動画 URL を Discord に送信しました'}), 200
    return jsonify({'message': '動画 URL が見つかりませんでした'}), 400

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
