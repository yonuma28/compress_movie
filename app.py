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

class VideoUploadModal(ui.Modal, title='動画アップロード'):
    video_title = ui.TextInput(label='動画のタイトル', placeholder='動画のタイトルを入力してください', required=True)
    video_category = ui.TextInput(label='カテゴリ (気持ちいい clips / 笑える clips)', placeholder='例: 気持ちいい clips', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        title = self.video_title.value
        category = self.video_category.value

        # カテゴリに基づいてチャンネルIDを設定
        channel_id = None
        if category == '気持ちいい clips':
            channel_id = os.getenv('GOOD_CHANNEL_ID') # 環境変数から取得
        elif category == '笑える clips':
            channel_id = os.getenv('FUNNY_CHANNEL_ID') # 環境変数から取得

        if not channel_id:
            await interaction.response.send_message('無効なカテゴリです。', ephemeral=True)
            return

        await interaction.response.send_message(
            f'''タイトル: `{title}`, カテゴリ: `{category}` で動画をアップロードします。
**このメッセージに動画ファイルを添付して送信してください。**''',
            ephemeral=False # 他のユーザーにも見えるようにする
        )
        # ユーザーの次のメッセージを待つために情報を保存
        bot.waiting_for_video[interaction.user.id] = {
            'title': title,
            'category': category,
            'channel_id': int(channel_id),
            'uploader_id': interaction.user.id,
            'uploader_mention': interaction.user.mention
        }


@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')
    # スラッシュコマンドを同期
    await bot.tree.sync()
    logger.info('Slash commands synced.')
    bot.waiting_for_video = {} # ユーザーからの動画添付を待つための辞書

@bot.tree.command(name="upload", description="動画をアップロードします")
async def upload_command(interaction: discord.Interaction):
    await interaction.response.send_modal(VideoUploadModal())

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
                category = user_data['category']
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
                        await target_channel.send(f"[{title} - {category}]({video_url}) (Uploaded by: {uploader_mention})")
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