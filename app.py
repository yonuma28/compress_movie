from flask import Flask, request, render_template
import os
import moviepy.editor as mp
import discord
from discord.ext import commands

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'  # アップロードされたファイルを保存するフォルダ
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Discordボットの設定
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.getenv('TOKEN')

# 動画を圧縮する関数
def compress_video(input_file, output_file, target_size):
    video = mp.VideoFileClip(input_file)
    video.write_videofile(output_file, codec='libx264', bitrate=target_size)
    video.close()

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/text', methods=['POST'])
def receive_text():
    text = request.form['text']
    print("受け取ったテキスト:", text)  # ターミナルに表示
    return "テキストを受け取りました", 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'ファイルが見つかりませんでした。'
    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が空です。'
    
    # アップロードされたファイルを保存
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # 動画を圧縮
    compressed_file_path = os.path.join(UPLOAD_FOLDER, 'compressed_' + file.filename)
    compress_video(file_path, compressed_file_path, "500k")  # 500kbpsで圧縮

    # Discordに送信
    send_to_discord(compressed_file_path)

    return 'ファイルがアップロードされ、圧縮されました！'

def send_to_discord(file_path):
    @bot.event
    async def on_ready():
        channel = bot.get_channel(1244248370307010654)  # 送信先のチャンネルIDを指定
        await channel.send(file=discord.File(file_path))

    bot.run(TOKEN)  # ボットのトークンを指定

if __name__ == '__main__':
    app.run(debug=True)