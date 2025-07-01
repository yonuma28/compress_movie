import os
import asyncio
import cloudinary
import cloudinary.uploader
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, request, render_template, redirect, url_for

import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24) # セッション管理のためのシークレットキー

TOKEN = os.getenv('TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'http://127.0.0.1:5000') # デフォルトはローカル開発用

cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

intents = discord.Intents.default()
intents.message_content = True # メッセージの内容を読み取るために必要
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')
    # スラッシュコマンドを同期
    bot.tree.clear_commands(guild=None) # 全てのギルドからコマンドをクリア
    await bot.tree.sync()
    logger.info('Slash commands synced.')

@app.route('/upload_web', methods=['GET', 'POST'])
async def upload_web():
    if request.method == 'GET':
        # GETリクエストの場合は、クエリパラメータからタイトルとチャンネルIDを取得してフォームに渡す
        title = request.args.get('title', '')
        channel_id = request.args.get('channel_id', '')
        return render_template('upload.html', initial_title=title, initial_channel_id=channel_id,
                               good_channel_id=os.getenv('GOOD_CHANNEL_ID'),
                               b2b_channel_id=os.getenv('B2B_CHANNEL_ID'))

    # POSTリクエストの場合
    if 'video' not in request.files:
        return redirect(request.url)

    video_file = request.files['video']
    title = request.form.get('title', '') # タイトルがなくてもOK
    channel_id_str = request.form.get('channel_id') # フォームから直接channel_idを取得

    if video_file.filename == '':
        return redirect(request.url)

    if video_file and channel_id_str:
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            return redirect(request.url)

        # チャンネル名を取得（表示用）
        channel_name = ""
        if str(channel_id) == os.getenv('GOOD_CHANNEL_ID'):
            channel_name = '気持ちいい clips'
        elif str(channel_id) == os.getenv('B2B_CHANNEL_ID'):
            channel_name = 'B2B clips'
        else:
            return redirect(request.url)

        temp_file_path = os.path.join('/tmp', video_file.filename) # /tmp に保存
        await asyncio.to_thread(video_file.save, temp_file_path)

        try:
            logger.info(f"Uploading video to Cloudinary from web: {temp_file_path}")
            upload_result = cloudinary.uploader.upload(
                temp_file_path, resource_type='video', eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
            )
            video_url = upload_result['secure_url']
            logger.info(f"Upload successful. Video URL: {video_url}")

            os.remove(temp_file_path)

            target_channel = bot.get_channel(channel_id)
            if isinstance(target_channel, discord.TextChannel):
                message_content = f"[ウェブアップロード: {channel_name}]({video_url})"
                if title:
                    message_content = f"[ウェブアップロード: {title} - {channel_name}]({video_url})"
                await target_channel.send(message_content)
            else:
                logger.error(f"Invalid target channel for web upload: {channel_id}")

        except Exception as e:
            logger.error(f"Error during web video upload and Discord send: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        return redirect(url_for('index'))
    return redirect(request.url)

from typing import Literal

@bot.tree.command(name="upload", description="動画をアップロードします")
@app_commands.describe(channel="アップロード先のチャンネル", title="動画のタイトル (任意)")
async def upload_command(interaction: discord.Interaction, channel: Literal['気持ちいい clips', 'B2B clips'], title: str = ""):
    await interaction.response.defer(ephemeral=True)

    channel_id = None
    channel_name = ""

    if channel == '気持ちいい clips':
        channel_id = os.getenv('GOOD_CHANNEL_ID')
        channel_name = '気持ちいい clips'
    elif channel == 'B2B clips':
        channel_id = os.getenv('B2B_CHANNEL_ID')
        channel_name = 'B2B clips'

    if not channel_id:
        await interaction.followup.send('チャンネルの選択が無効です。', ephemeral=True)
        return

    upload_url = f"{WEB_APP_URL}?title={title}&channel_id={channel_id}"

    await interaction.followup.send(
        f'タイトル: `{title}`, チャンネル: `{channel_name}` に動画をアップロードします。\n'
        f'以下のURLにアクセスして動画ファイルをアップロードしてください。\n'
        f'<{upload_url}>',
        ephemeral=True
    )

if __name__ == '__main__':
    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    bot.run(TOKEN)