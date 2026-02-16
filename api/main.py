import os, requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, AudioMessage, TextSendMessage

# ประกาศ app ไว้ด้านบนสุดและห้ามมีตัวแปรชื่อ app อื่นๆ ในไฟล์
app = Flask(__name__) 

# ย้ายการดึงค่า Config ไว้ในตัวแปรที่ชื่อชัดเจน
LINE_API = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
LINE_HANDLER = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
D_KEY = os.getenv('DIFY_API_KEY')
D_URL = os.getenv('DIFY_BASE_URL', 'http://bt-dify.demotoday.net/v1')

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        LINE_HANDLER.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ... ส่วน handle_audio ให้ใช้ LINE_API และ LINE_HANDLER ตามชื่อใหม่ ...

# สำคัญ: ห้ามมี app.run() อยู่นอก if __name__ == "__main__": เด็ดขาด
if __name__ == "__main__":
    app.run()