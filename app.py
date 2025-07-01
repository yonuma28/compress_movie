import os
import asyncio
import cloudinary
import cloudinary.uploader
import discord
from discord.ext import commands
from discord import app_commands, ui
from flask import Flask, request, render_template, redirect, url_for
from typing import Literal

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

class VideoTitleModal(ui.Modal, title='動画のタイトルを入力'):
    video_title = ui.TextInput(label='動画のタイトル', placeholder='動画のタイトルを入力してください (任意)', required=False)

    def __init__(self, selected_channel_id: int, selected_channel_name: str):
        super().__init__()
        self.selected_channel_id = selected_channel_id
        self.selected_channel_name = selected_channel_name

    async def on_submit(self, interaction: discord.Interaction):
        title = self.video_title.value if self.video_title.value else ""
        
        # ウェブアップロード用のURLを生成
        upload_url = f"{WEB_APP_URL}?title={title}&channel_id={self.selected_channel_id}"

        await interaction.response.send_message(
            f'タイトル: `{title}`, チャンネル: `{self.selected_channel_name}` に動画をアップロードします。\n'
            f'以下のURLにアクセスして動画ファイルをアップロードしてください。\n'
            f'<{upload_url}>', # URLを埋め込みリンクとして表示
            ephemeral=True # 他のユーザーには見えないようにする
        )

class ChannelSelectView(ui.View):
    def __init__(self):
        super().__init__(timeout=180) # 3分でタイムアウト

    @ui.select(
        placeholder='動画をアップロードするチャンネルを選択してください',
        options=[
            discord.SelectOption(label='気持ちいい clips', value='good_clips'),
            discord.SelectOption(label='B2B clips', value='funny_clips') # valueはそのままにしておく
        ]
    )
    async def select_channel(self, interaction: discord.Interaction, select: ui.Select):
        selected_value = select.values[0]
        channel_id = None
        channel_name = ""

        if selected_value == 'good_clips':
            channel_id = os.getenv('GOOD_CHANNEL_ID')
            channel_name = '気持ちいい clips'
        elif selected_value == 'funny_clips':
            channel_id = os.getenv('B2B_CHANNEL_ID') # ここをB2B_CHANNEL_IDに変更
            channel_name = 'B2B clips' # ここをB2B clipsに変更

        if not channel_id:
            await interaction.response.send_message('チャンネルの選択が無効です。', ephemeral=True)
            return

        # チャンネルが選択されたら、タイトル入力モーダルを表示
        await interaction.response.send_modal(VideoTitleModal(int(channel_id), channel_name))
        self.stop() # Viewを停止して、これ以上選択できないようにする


@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')
    await bot.tree.sync()
    logger.info('Slash commands synced.')

@app.route('/')
def index():
    return redirect(url_for('upload_web', **request.args))

@app.route('/upload_web', methods=['GET', 'POST'])
async def upload_web():
    if request.method == 'GET':
        title = request.args.get('title', '')
        channel_id = request.args.get('channel_id', '')
        author = request.args.get('author', '')
        return render_template('upload.html', initial_title=title, initial_channel_id=channel_id, initial_author=author,
                               good_channel_id=os.getenv('GOOD_CHANNEL_ID'),
                               b2b_channel_id=os.getenv('B2B_CHANNEL_ID'))

    if 'video' not in request.files:
        return redirect(request.url)

    video_file = request.files['video']
<<<<<<< HEAD
    title = request.form.get('title', '') # タイトルがなくてもOK
    channel_id_str = request.form.get('channel_id') # フォームから直接channel_idを取得
=======
    title = request.form.get('title')
    channel_id_str = request.form.get('channel_id')
    author = request.form.get('author')
>>>>>>> 9259c5d66bd51e467ebddec81e2df7bcf51f5ba3

    if video_file.filename == '':
        return redirect(request.url)

    if video_file and channel_id_str:
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            return redirect(request.url)

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
<<<<<<< HEAD
                message_content = f"[ウェブアップロード: {channel_name}]({video_url})"
                if title:
                    message_content = f"[ウェブアップロード: {title} - {channel_name}]({video_url})"
                await target_channel.send(message_content)
                flash('動画が正常にアップロードされ、Discordに送信されました。')
=======
                message = f"[{author} - {title}]({video_url})"
                future = asyncio.run_coroutine_threadsafe(
                    target_channel.send(message),
                    bot.loop
                )
                future.result()
>>>>>>> 9259c5d66bd51e467ebddec81e2df7bcf51f5ba3
            else:
                logger.error(f"Invalid target channel for web upload: {channel_id}")

        except Exception as e:
            logger.error(f"Error during web video upload and Discord send: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        return redirect(url_for('index'))
    return redirect(request.url)

@bot.tree.command(name="upload", description="動画をアップロードします")
@app_commands.describe(channel="アップロード先のチャンネル", title="動画のタイトル")
async def upload_command(interaction: discord.Interaction, channel: Literal['気持ちいい clips', 'B2B clips'], title: str):
    await interaction.response.defer(ephemeral=True)

    author = interaction.user.display_name
    channel_id = None

    if channel == '気持ちいい clips':
        channel_id = os.getenv('GOOD_CHANNEL_ID')
    elif channel == 'B2B clips':
        channel_id = os.getenv('B2B_CHANNEL_ID')

    if not channel_id:
        return

    upload_url = f"{WEB_APP_URL}?title={title}&channel_id={channel_id}&author={author}"

    await interaction.followup.send(
        f'タイトル: `{title}`, チャンネル: `{channel}` に動画をアップロードします。\n'
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