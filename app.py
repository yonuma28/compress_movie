import os
import asyncio
import threading
from flask import Flask, request, render_template
import cloudinary
import cloudinary.uploader
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
TOKEN = os.getenv('TOKEN')
CHANNEL_ID = 1244248370307010654  # 送信先のチャンネルID

intents = discord.Intents.default()
intents.messages = True  # メッセージ送信を有効化
intents.guilds = True    # ギルド情報を取得可能にする

bot = commands.Bot(command_prefix='!', intents=intents)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """動画を受け取り、Cloudinaryにアップロードし、Discordに送信"""
    if 'file' not in request.files:
        return 'ファイルが見つかりませんでした。'
    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が空です。'

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # 非同期で動画をアップロード・送信
    threading.Thread(target=process_and_send, args=(file_path,)).start()

    return render_template('upload.html', message='ファイルがアップロードされました！')

def process_and_send(file_path):
    """動画をCloudinaryにアップロードし、Discordに送信"""
    upload_result = cloudinary.uploader.upload(
        file_path,
        resource_type='video',
        eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
    )

    compressed_video_url = upload_result['eager'][0]['secure_url']

    # bot.loop を使ってタスクをスケジュール
    bot.loop.create_task(send_to_discord(compressed_video_url))

async def send_to_discord(video_url):
    """Discordに動画のURLを送信"""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)
    await channel.send(video_url)

@bot.event
async def on_ready():
    """Botが起動したときに通知を送信"""
    print(f'Logged in as {bot.user}')
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("Bot is online!")

@bot.command()
async def test(ctx):
    """!test コマンドでメッセージを送信"""
    await ctx.send("Test message from bot!")

def run_flask():
    """Flaskアプリを実行"""
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    # Flask を別スレッドで実行
    threading.Thread(target=run_flask).start()

    # Discord Bot を実行
    asyncio.run(bot.start(TOKEN))
