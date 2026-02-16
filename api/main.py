import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, AudioMessage, TextSendMessage
from supabase import create_client

# 1. ต้องมั่นใจว่าประกาศ app ไว้ที่ระดับนอกสุดของไฟล์
app = Flask(__name__)

# ตั้งค่า API Keys
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

@app.route("/", methods=['GET'])
def index():
    return "Hello, Secretary AI is running!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    if event.message.text == "คุณเลขา":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="บอท AI พร้อมสรุปประชุมแล้วค่ะ")
        )

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    # จดงานลง Supabase
    supabase.table("audio_tasks").insert({
        "audio_id": event.message.id,
        "user_id": event.source.user_id,
        "status": "pending"
    }).execute()
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="⏳ ได้รับไฟล์เสียงแล้วค่ะ เครื่อง Server กำลังสรุปให้ กรุณารอสักครู่นะคะ")
    )

# 2. ห้ามใช้ app.run() ในไฟล์ที่จะรันบน Vercel
# เพราะ Vercel จะเป็นคนจัดการเรื่อง Server ให้เองครับ