from flask import Flask, request, abort
import os
import datetime

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# LINE
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# ===== LINE設定 =====
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== Google Sheets設定 =====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

import json

creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("家計簿").sheet1

# ===== 動作確認 =====
@app.route("/")
def home():
    return "OK"

# ===== Webhook =====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ===== メッセージ受信 =====
@handler.add(MessageEvent)
def handle_message(event):
    text = event.message.text

    # ===== ヘルプ =====
    if text == "ヘルプ":
        reply = """📊 家計簿BOT

【登録】
ランチ 800

【確認】
今月
"""
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # ===== 今月合計 =====
    if text == "今月":
        data = sheet.get_all_values()[1:]

        total = 0
        msg = "【今月の支出】\n"

        for row in data:
            if row[3] == "支出":
                total += int(row[2])

        msg += f"\n合計：{total}円"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # ===== 登録 =====
    try:
        content, amount = text.split(" ")
        today = str(datetime.date.today())

        sheet.append_row([
            today,
            content,
            amount,
            "支出",
            ""
        ])

        reply = f"{content} {amount}円 登録しました 👍"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    except:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="入力形式が違うよ！例：ランチ 800")
        )