import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, AudioMessage, TextSendMessage
from supabase import create_client

app = Flask(__name__)

# ENV จาก Vercel
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

@app.route("/")
def index():
    return "Secretary Bot Online"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    if event.message.text == "คุณเลขา":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🤖 AI Secretary พร้อมรับไฟล์เสียงค่ะ")
        )

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio(event):
    supabase.table("audio_tasks").insert({
        "audio_id": event.message.id,
        "user_id": event.source.user_id,
        "status": "pending"
    }).execute()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="⏳ รับไฟล์เสียงแล้ว กำลังประมวลผลค่ะ")
    )
