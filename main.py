import os
import requests
from flask import Flask, request, abort
from pydub import AudioSegment
from openai import OpenAI
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, AudioMessage, TextSendMessage

app = Flask(__name__)

# --- Configuration ---
# แนะนำให้นำค่าเหล่านี้ไปใส่ใน Railway Variables เพื่อความปลอดภัย
LINE_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_KEY)
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)

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
    message_id = event.message.id
    user_id = event.source.user_id
    
    # ตอบกลับทันทีเพื่อป้องกัน Timeout
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⏳ ได้รับไฟล์เสียงแล้ว ระบบกำลังประมวลผลสรุปการประชุม (อาจใช้เวลา 5-10 นาทีสำหรับไฟล์ยาว) โปรดรอสักครู่..."))

    # 1. ดาวน์โหลดไฟล์เสียงจาก LINE
    message_content = line_bot_api.get_message_content(message_id)
    input_file = f"{message_id}.m4a"
    with open(input_file, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    try:
        # 2. กระบวนการแปลงเสียงเป็นข้อความ (STT) โดยแบ่งไฟล์
        full_transcript = process_stt_with_chunks(input_file)
        
        # 3. ส่งไปสรุปเนื้อหาด้วย Prompt ที่คุณตั้งไว้
        summary_result = get_ai_summary(full_transcript)
        
        # 4. ส่งผลลัพธ์กลับหาผู้ใช้ (Push Message)
        line_bot_api.push_message(user_id, TextSendMessage(text=summary_result))
        
    except Exception as e:
        line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ เกิดข้อผิดพลาด: {str(e)}"))
    finally:
        # ลบไฟล์ออกจาก Server เพื่อประหยัดพื้นที่
        if os.path.exists(input_file): os.remove(input_file)

def process_stt_with_chunks(file_path):
    audio = AudioSegment.from_file(file_path)
    # แบ่งทุก 15 นาที (เพื่อให้ขนาดไฟล์ไม่เกิน 25MB ของ OpenAI)
    chunk_length = 15 * 60 * 1000 
    chunks = [audio[i:i + chunk_length] for i in range(0, len(audio), chunk_length)]
    
    full_text = ""
    for i, chunk in enumerate(chunks):
        chunk_name = f"temp_{i}.mp3"
        chunk.export(chunk_name, format="mp3")
        with open(chunk_name, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            full_text += transcript.text + " "
        os.remove(chunk_name)
    return full_text

def get_ai_summary(transcript):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": """คุณคือผู้ช่วยจดบันทึกการประชุมมืออาชีพ (Professional Minute Taker) 
                หน้าที่ของคุณคือสรุปเนื้อหาจากข้อความที่แปลงมาจากเสียงการประชุม (Transcription) 
                โดยให้แสดงผลลัพธ์ในรูปแบบ Markdown ดังนี้:

                # 🗓 ชื่อการประชุม
                [วิเคราะห์ชื่อการประชุมที่เหมาะสมที่สุดจากเนื้อหา]

                ## 📝 เนื้อหาสรุป
                - [สรุปประเด็นสำคัญเป็นข้อๆ แบ่งตามหัวข้อการสนทนา]
                - [ระบุใจความสำคัญที่ตกลงกันได้]

                ## 🚀 Next Step (สิ่งที่ต้องทำต่อ)
                - [ระบุสิ่งที่ต้องทำ: ใครเป็นคนรับผิดชอบ | กำหนดส่ง (ถ้ามี)]
                - [หากไม่ระบุชื่อคน ให้เขียนว่า 'ทีมที่เกี่ยวข้อง']

                **หมายเหตุ:** ตอบเป็นภาษาไทยที่กระชับ สละสลวย และเป็นทางการ"""
            },
            {"role": "user", "content": f"นี่คือเนื้อหาจากการประชุม: {transcript}"}
        ],
        temperature=0.5
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))