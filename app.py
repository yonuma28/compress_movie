import os
from flask import Flask, request, render_template
import cloudinary
import cloudinary.uploader
import asyncio
import threading
import discord
from discord.ext import commands

app = Flask(__name__)

# Cloudinaryの設定
cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

# Discordボットの設定
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.getenv('TOKEN')
CHANNEL_ID = 1244248370307010654  # 送信先のチャンネルIDを指定

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'ファイルが見つかりませんでした。'
    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が空です。'

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # 動画をCloudinaryにアップロード
    upload_result = cloudinary.uploader.upload(
        file_path,
        resource_type='video',
        eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
    )

    # 圧縮後の動画URLを取得
    compressed_video_url = upload_result['eager'][0]['secure_url']

    # Discordに非同期で送信
    loop = asyncio.new_event_loop()
    threading.Thread(target=run_discord_bot, args=(compressed_video_url, loop)).start()

    return render_template('upload.html', message='ファイルがアップロードされ、圧縮されました！')

def run_discord_bot(video_url, loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_to_discord(video_url))

async def send_to_discord(video_url):
    async with bot:
        await bot.start(TOKEN)
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(video_url)
        await bot.close()

if __name__ == '__main__':
    app.run(debug=True)
