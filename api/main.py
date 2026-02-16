import os
import time
import whisper
from flask import Flask, request
from supabase import create_client
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, AudioMessage, TextSendMessage
from dotenv import load_dotenv

# 1. โหลดความลับจากไฟล์ .env (ต้องกด Save ไฟล์ .env ก่อนรันนะ!)
load_dotenv()

app = Flask(__name__)

# ตั้งค่าการเชื่อมต่อ
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

print("🔍 [1/3] กำลังโหลด Whisper Model (Turbo)...", flush=True)
model = whisper.load_model("turbo") 
print("✅ [2/3] โหลด Model สำเร็จ!", flush=True)

# ส่วนรับงาน (Webhook) - เลียนแบบสิ่งที่ Vercel จะทำ
@app.route("/callback", methods=['POST'])
def callback():
    # โค้ดส่วนนี้จะรับงานจาก LINE แล้วเอาไปใส่ใน Supabase
    return 'OK'

def run_worker():
    """ฟังก์ชันเฝ้าดูคิวงานใน Supabase (เหมือนเครื่อง Server)"""
    print("🚀 [3/3] ระบบพร้อมทำงาน! กำลังเฝ้าดูคิวงาน...", flush=True)
    while True:
        try:
            res = supabase.table("audio_tasks").select("*").eq("status", "pending").limit(1).execute()
            if res.data:
                task = res.data[0]
                print(f"📦 พบงานใหม่ ID: {task['audio_id']}", flush=True)
                
                # อัปเดตเป็นกำลังทำ
                supabase.table("audio_tasks").update({"status": "processing"}).eq("id", task['id']).execute()
                
                # ประมวลผล
                content = line_bot_api.get_message_content(task['audio_id'])
                with open("temp.m4a", "wb") as f:
                    for chunk in content.iter_content(): f.write(chunk)
                
                result = model.transcribe("temp.m4a", language="th")
                line_bot_api.push_message(task['user_id'], TextSendMessage(text=f"สรุปเสียง: {result['text']}"))
                
                # จบงาน
                supabase.table("audio_tasks").update({"status": "completed"}).eq("id", task['id']).execute()
                os.remove("temp.m4a")
                print("✅ งานเสร็จสมบูรณ์!", flush=True)
        except Exception as e:
            print(f"❌ Error: {e}", flush=True)
        time.sleep(5)

if __name__ == "__main__":
    # ในการทดสอบเครื่องเรา เราจะรันเฉพาะตัว Worker ก่อน
    run_worker()