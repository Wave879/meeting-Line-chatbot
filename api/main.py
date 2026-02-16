import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, AudioMessage, TextSendMessage
from supabase import create_client

# 1. ต้องอยู่ระดับนอกสุด (Global) เท่านั้น เพื่อให้ Vercel Runtime หาเจอ
app = Flask(__name__)

# 2. โหลด Config จาก Vercel Environment Variables
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

@app.route("/")
def home():
    return "Secretary AI Online"

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
            TextSendMessage(text="บอท AI พร้อมสรุปประชุมแล้วค่ะ ส่งไฟล์เสียงมาได้เลย")
        )

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    # จดงานลงคิวใน Supabase
    supabase.table("audio_tasks").insert({
        "audio_id": str(event.message.id),
        "user_id": str(event.source.user_id),
        "status": "pending"
    }).execute()
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="⏳ ได้รับไฟล์เสียงแล้วค่ะ กำลังประมวลผลสรุปให้นะคะ")
    )