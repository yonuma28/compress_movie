import os
import asyncio
import cloudinary
import cloudinary.uploader
import discord
from discord.ext import commands
from discord import app_commands, ui

import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TOKEN')
# CHANNEL_ID はコマンド内で動的に取得するため、ここでは不要
# UPLOAD_FOLDER はDiscordの添付ファイルとして処理するため不要

cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

intents = discord.Intents.default()
intents.message_content = True # メッセージの内容を読み取るために必要
bot = commands.Bot(command_prefix="!", intents=intents)

class VideoTitleModal(ui.Modal, title='動画のタイトルを入力'):
    video_title = ui.TextInput(label='動画のタイトル', placeholder='動画のタイトルを入力してください', required=True)

    def __init__(self, selected_channel_id: int, selected_channel_name: str):
        super().__init__()
        self.selected_channel_id = selected_channel_id
        self.selected_channel_name = selected_channel_name

    async def on_submit(self, interaction: discord.Interaction):
        title = self.video_title.value

        await interaction.response.send_message(
            f'''タイトル: `{title}`, チャンネル: `{self.selected_channel_name}` に動画をアップロードします。
**このメッセージに動画ファイルを添付して送信してください。**''',
            ephemeral=False
        )
        bot.waiting_for_video[interaction.user.id] = {
            'title': title,
            'channel_name': self.selected_channel_name,
            'channel_id': self.selected_channel_id,
            'uploader_id': interaction.user.id,
            'uploader_mention': interaction.user.mention
        }

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
    # スラッシュコマンドを同期
    await bot.tree.sync()
    logger.info('Slash commands synced.')
    bot.waiting_for_video = {} # ユーザーからの動画添付を待つための辞書

@bot.tree.command(name="upload", description="動画をアップロードします")
async def upload_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        '動画をアップロードするチャンネルを選択してください。',
        view=ChannelSelectView(),
        ephemeral=True # 他のユーザーには見えないようにする
    )

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.author.id in bot.waiting_for_video:
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith('video/'):
                user_data = bot.waiting_for_video.pop(message.author.id)
                title = user_data['title']
                channel_name = user_data['channel_name'] # channel_name を取得
                channel_id = user_data['channel_id']

                await message.channel.send(f'動画のアップロードを開始します: `{attachment.filename}`', reference=message)
                
                try:
                    # 動画を一時的に保存
                    temp_file_path = f"temp_{attachment.filename}"
                    await attachment.save(temp_file_path)

                    logger.info(f"Uploading video to Cloudinary: {temp_file_path}")
                    upload_result = cloudinary.uploader.upload(
                        temp_file_path, resource_type='video', eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
                    )
                    video_url = upload_result['secure_url']
                    logger.info(f"Upload successful. Video URL: {video_url}")

                    # 一時ファイルを削除
                    os.remove(temp_file_path)

                    target_channel = bot.get_channel(channel_id)
                    if isinstance(target_channel, discord.TextChannel):
                        uploader_mention = user_data.get('uploader_mention', '不明なユーザー')
                        await target_channel.send(f"[{title} - {channel_name}]({video_url}) (Uploaded by: {uploader_mention})")
                        await message.channel.send('動画が正常にアップロードされ、Discordに送信されました。', reference=message)
                    else:
                        logger.error(f"Invalid target channel: {channel_id}")
                        await message.channel.send('指定されたチャンネルが見つからないか、テキストチャンネルではありません。', reference=message)

                except Exception as e:
                    logger.error(f"Error during video upload and Discord send: {e}")
                    await message.channel.send(f'動画のアップロード中にエラーが発生しました: {e}', reference=message)
            else:
                await message.channel.send('添付ファイルが動画ではありません。動画ファイルを添付してください。', reference=message)
        else:
            await message.channel.send('動画ファイルが添付されていません。動画ファイルを添付して送信してください。', reference=message)
    
    await bot.process_commands(message) # コマンド処理を継続するために必要

if __name__ == '__main__':
    bot.run(TOKEN)