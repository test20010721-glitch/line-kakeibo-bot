from flask import Flask, request, abort
import os
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 環境変数から取得
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 動作確認
@app.route("/")
def home():
    return "OK"

# Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# メッセージ受信
@handler.add(MessageEvent)
def handle_message(event):
    text = event.message.text

    if text == "ヘルプ":
        reply = "使い方：ランチ 800 などと送ってね 👍"
    else:
        reply = f"{text} 受け取りました 👍"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )