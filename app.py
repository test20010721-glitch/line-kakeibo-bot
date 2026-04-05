from flask import Flask, request
from linebot import LineBotApi
from linebot.models import TextSendMessage
import os

app = Flask(__name__)

# 環境変数から取得（Renderで設定したやつ）
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)


# トップページ（Render確認用）
@app.route("/")
def home():
    return "OK"


# LINE Webhook
@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json()

    # eventsがない場合対策
    if "events" not in body:
        return "OK"

    event = body["events"][0]

    # メッセージじゃない場合スキップ
    if event["type"] != "message":
        return "OK"

    reply_token = event["replyToken"]
    text = event["message"]["text"]

    # ===== ヘルプ =====
    HELP = """📊 家計簿BOT

【登録】
ランチ 800

【確認】
今月

【削除】
削除 1

【変更】
変更 1 500
"""

    # ===== ヘルプ表示 =====
    if text == "ヘルプ":
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=HELP)
        )
        return "OK"

    # ===== 今は全部ダミー動作 =====
    if text == "今月":
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="今月の機能は準備中です")
        )
        return "OK"

    if text.startswith("削除"):
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="削除機能は準備中です")
        )
        return "OK"

    if text.startswith("変更"):
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="変更機能は準備中です")
        )
        return "OK"

    # ===== 登録（簡易版） =====
    try:
        content, amount = text.split(" ")
        reply = f"{content} {amount}円 登録しました 👍"

        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply)
        )

    except:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=HELP)
        )

    return "OK"
