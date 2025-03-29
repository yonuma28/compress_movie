import os
import time
import requests
import threading
from flask import Flask, request, render_template
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# Cloudinary の設定
cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

REPLIT_URL = "https://your-replit-app.repl.co/keep_alive"  # Replit のエンドポイント
REPLIT_DISCORD_ENDPOINT = "https://your-replit-app.repl.co/send_video"  # 動画URL送信用エンドポイント

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """動画を受け取り、Cloudinary にアップロードし、Replit に送信"""
    if 'file' not in request.files:
        return 'ファイルが見つかりませんでした。'
    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が空です。'

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    threading.Thread(target=process_and_upload, args=(file_path,)).start()

    return render_template('upload.html', message='ファイルがアップロードされました！')

def process_and_upload(file_path):
    """動画を Cloudinary にアップロードし、Replit に送信"""
    upload_result = cloudinary.uploader.upload(
        file_path,
        resource_type='video',
        eager=[{'width': 800, 'height': 600, 'crop': 'limit'}]
    )
    video_url = upload_result['secure_url']
    print(f"Uploaded: {video_url}")

    # Replit の Discord BOT に動画 URL を送信
    try:
        response = requests.post(REPLIT_DISCORD_ENDPOINT, json={"video_url": video_url})
        print(f"Sent video URL to Replit: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending video URL: {e}")

def ping_replit():
    """Replit の BOT を維持するため、5 分おきにリクエストを送る"""
    while True:
        try:
            response = requests.get(REPLIT_URL)
            print(f"Ping to Replit: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error sending ping: {e}")

        time.sleep(300)  # 5 分おき（300秒）

if __name__ == '__main__':
    # Replit を維持するスレッドを起動
    threading.Thread(target=ping_replit, daemon=True).start()

    # Flask アプリを実行
    app.run(debug=True, use_reloader=False)
