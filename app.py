import os
import asyncio
import cloudinary
import cloudinary.uploader
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask, request, render_template, redirect, url_for
from urllib.parse import quote_plus

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
        title = request.args.get('title', '')
        channel_id = request.args.get('channel_id', '')
        author = request.args.get('author', '')
        return render_template('upload.html', initial_title=title, initial_channel_id=channel_id, initial_author=author)

    # POSTリクエストの場合
    if 'video' not in request.files:
        return "動画ファイルが見つかりません。", 400

    video_file = request.files['video']
    title = request.form.get('title', '')
    channel_id_str = request.form.get('channel_id')
    author = request.form.get('author', '不明なユーザー')

    if video_file.filename == '':
        return "ファイルが選択されていません。", 400

    if video_file and channel_id_str:
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            return "無効なチャンネルIDです。", 400

        temp_file_path = os.path.join('/tmp', video_file.filename)
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
                if title:
                    message_content = f"[{author} - {title}]({video_url})"
                else:
                    message_content = f"[{author}]({video_url})"
                await target_channel.send(message_content)
            else:
                logger.error(f"Invalid target channel for web upload: {channel_id}")
                return "指定されたチャンネルが見つかりませんでした。", 500

        except Exception as e:
            logger.error(f"Error during web video upload and Discord send: {e}")
            return "サーバーエラーが発生しました。", 500
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        return "動画のアップロードが完了しました。"
    
    return "不正なリクエストです。", 400

from typing import Literal, Optional

@bot.tree.command(name="upload", description="動画をアップロードします")
@app_commands.describe(channel="アップロード先のチャンネル", title="動画のタイトル（任意）")
async def upload_command(interaction: discord.Interaction, channel: Literal['気持ちいい clips', 'B2B clips'], title: Optional[str] = None):
    await interaction.response.defer(ephemeral=True)

    channel_id = None
    if channel == '気持ちいい clips':
        channel_id = os.getenv('GOOD_CHANNEL_ID')
    elif channel == 'B2B clips':
        channel_id = os.getenv('B2B_CHANNEL_ID')

    if not channel_id:
        await interaction.followup.send('チャンネルの選択が無効です。', ephemeral=True)
        return

    # URLに含めるパラメータをエンコード
    url_title = quote_plus(title) if title else ""
    author = quote_plus(interaction.user.display_name)

    upload_url = f"{WEB_APP_URL}/upload_web?title={url_title}&channel_id={channel_id}&author={author}"

    await interaction.followup.send(
        f"こちらのリンクから動画をアップロードしてください： {upload_url}",
        ephemeral=True
    )

if __name__ == '__main__':
    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    bot.run(TOKEN)