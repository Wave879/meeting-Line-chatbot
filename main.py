import os, requests
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, AudioMessage, TextSendMessage

app = Flask(__name__)

# ดึงค่าจาก Environment Variables ใน Vercel Settings
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
DIFY_API_KEY = os.getenv('DIFY_API_KEY')

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    # 1. ตอบกลับทันทีเพื่อไม่ให้ Vercel ตัดการทำงาน
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⏳ รับไฟล์เสียงแล้ว Dify กำลังประมวลผลให้นะครับ..."))

    # 2. ส่งข้อมูลไปให้ Dify API ทำงานต่อ
    dify_url = "https://api.dify.ai/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "inputs": {
            "audio_id": event.message.id,
            "user_id": event.source.user_id
        },
        "response_mode": "no_streaming",
        "user": event.source.user_id
    }
    # ส่งแบบ Background (ไม่ต้องรอผลลัพธ์)
    requests.post(dify_url, headers=headers, json=data)

if __name__ == "__main__":
    app.run()