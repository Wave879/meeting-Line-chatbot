import os, requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, AudioMessage, TextSendMessage

app = Flask(__name__)

# ดึงค่าจาก Vercel Environment Variables
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
DIFY_API_KEY = os.getenv('DIFY_API_KEY')
DIFY_BASE_URL = os.getenv('DIFY_BASE_URL', 'http://bt-dify.demotoday.net/v1')

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    # 1. ตอบกลับทันทีป้องกัน Timeout 10 วินาทีของ Vercel
    line_bot_api.reply_message(
        event.reply_token, 
        TextSendMessage(text="⏳ ได้รับไฟล์เสียงแล้วงับ ")
    )

    # 2. ส่งข้อมูลไปให้ Dify Workflow (ใช้ URL จากรูปที่ 2)
    dify_url = f"{DIFY_BASE_URL}/workflows/run"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": {
            "audio_id": event.message.id,
            "user_id": event.source.user_id
        },
        "response_mode": "no_streaming",
        "user": event.source.user_id
    }
    
    # ส่งแบบไม่ต้องรอผลลัพธ์ (Fire and Forget)
    try:
        requests.post(dify_url, headers=headers, json=payload, timeout=5)
    except requests.exceptions.ReadTimeout:
        pass # ปล่อยให้มันทำงานข้างหลังไป

if __name__ == "__main__":
    # สำหรับรันเทสในเครื่อง
    app.run(port=5000)