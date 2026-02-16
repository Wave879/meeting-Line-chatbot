import os
import time
import whisper
import threading
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, AudioMessage, TextMessage, TextSendMessage
from supabase import create_client
from dotenv import load_dotenv

# 1. โหลดค่า Config
load_dotenv()
app = Flask(__name__)

# เชื่อมต่อ API (ดึงจาก .env ในเครื่อง)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# 2. โหลด AI Model รอไว้ที่ H100
print("🔍 กำลังโหลด Whisper Turbo บน GPU...", flush=True)
model = whisper.load_model("turbo")
print("✅ ระบบ AI พร้อมใช้งาน!", flush=True)

# --- ส่วนที่ 1: SERVER (ทำหน้าที่แทน Vercel ในเครื่องคุณ) ---
@app.route("/callback", methods=['POST'])
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
    # บันทึกงานลง Supabase ทันที
    supabase.table("audio_tasks").insert({
        "audio_id": str(event.message.id),
        "user_id": str(event.source.user_id),
        "status": "pending"
    }).execute()
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🎙️ ได้รับบันทึกประชุมแล้วค่ะ กำลังประมวลผลสรุปให้นะคะ..."))

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    # ฟีเจอร์ @แท็ก
    if event.message.text in ["@everyone", "@all", "@ทุกคน"]:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📢 ประกาศจากคุณเลขา: ทุกคนคะ มีเรื่องสำคัญรบกวนอ่านด้านบนด้วยค่ะ! 🚨"))

# --- ส่วนที่ 2: WORKER (รันเบื้องหลังในเครื่องเดียวกัน) ---
def ai_worker():
    print("🤖 Worker กำลังเฝ้าดูคิวงาน...", flush=True)
    while True:
        try:
            res = supabase.table("audio_tasks").select("*").eq("status", "pending").limit(1).execute()
            if res.data:
                task = res.data[0]
                supabase.table("audio_tasks").update({"status": "processing"}).eq("id", task['id']).execute()
                
                # ดาวน์โหลดและประมวลผล
                content = line_bot_api.get_message_content(task['audio_id'])
                temp_file = f"temp_{task['audio_id']}.m4a"
                with open(temp_file, "wb") as f:
                    for chunk in content.iter_content(): f.write(chunk)
                
                print(f"📝 กำลังสรุปประชุม: {task['audio_id']}")
                result = model.transcribe(temp_file, language="th")
                summary = result['text']
                
                # ส่งผลลัพธ์พร้อม @แท็ก
                line_bot_api.push_message(task['user_id'], TextSendMessage(text=f"📋 สรุปประชุมเสร็จแล้วค่ะ:\n{summary}\n\n@ทุกคน โปรดตรวจสอบด้วยค่ะ"))
                
                supabase.table("audio_tasks").update({"status": "completed"}).eq("id", task['id']).execute()
                os.remove(temp_file)
                print("✅ งานเสร็จสิ้น!", flush=True)
        except Exception as e:
            print(f"❌ Worker Error: {e}", flush=True)
        time.sleep(5)

if __name__ == "__main__":
    # เปิดการทำงานของ Worker (Thread 1)
    threading.Thread(target=ai_worker, daemon=True).start()
    # เปิดการทำงานของ Server (Thread 2)
    app.run(port=5000)