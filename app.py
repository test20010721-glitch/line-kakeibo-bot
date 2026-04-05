from flask import Flask, request, abort
import os
import datetime
import json

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

# ===== メイン処理 =====
@handler.add(MessageEvent)
def handle_message(event):
    text = event.message.text.strip()
    today = datetime.date.today()
    current_month = today.month

    # ===== ヘルプ =====
    if text == "ヘルプ":
        reply = """📊 家計簿BOT

【支出】
ランチ 800

【収入】
+50000

【確認】
今月 / 3月

【削除】
削除 1

【変更】
変更 1 500
"""
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # ===== 月確認 =====
    if text == "今月" or text.endswith("月"):
        try:
            if text == "今月":
                target_month = current_month
            else:
                target_month = int(text.replace("月", ""))

            data = sheet.get_all_values()[1:]

            total_in = 0
            total_out = 0
            msg = f"【{target_month}月】\n"

            for row in data:
                if len(row) < 5:
                    continue

                date = row[1]
                month = int(date.split("-")[1])

                if month == target_month:
                    id_ = row[0]
                    content = row[2]
                    amount = int(row[3])
                    type_ = row[4]

                    msg += f"{id_}. {content} {amount}円\n"

                    if type_ == "収入":
                        total_in += amount
                    else:
                        total_out += amount

            balance = total_in - total_out

            # ±表示
            if balance >= 0:
                balance_text = f"+{balance}"
            else:
                balance_text = f"{balance}"

            msg += f"\n収入：{total_in}円"
            msg += f"\n支出：{total_out}円"
            msg += f"\n収支：{balance_text}円"

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="3月 の形式で入力してね"))
        return

    # ===== 削除 =====
    if text.startswith("削除"):
        try:
            target_id = text.split(" ")[1]
            data = sheet.get_all_values()

            for i, row in enumerate(data):
                if row and row[0] == target_id:
                    sheet.delete_rows(i + 1)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="削除しました 👍"))
                    return

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="IDが見つからないよ"))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="削除 1 の形式で入力してね"))
        return

    # ===== 変更 =====
    if text.startswith("変更"):
        try:
            parts = text.split(" ")
            target_id = parts[1]
            new_amount = parts[2]

            data = sheet.get_all_values()

            for i, row in enumerate(data):
                if row and row[0] == target_id:
                    sheet.update_cell(i + 1, 4, new_amount)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="変更しました 👍"))
                    return

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="IDが見つからないよ"))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="変更 1 500 の形式で入力してね"))
        return

    # ===== 登録 =====
    try:
        data = sheet.get_all_values()
        new_id = len(data)
        today_str = str(today)

        # 収入
        if text.startswith("+"):
            amount = text.replace("+", "")
            content = "収入"
            type_ = "収入"

        # 支出
        else:
            content, amount = text.split(" ")
            type_ = "支出"

        sheet.append_row([
            str(new_id),
            today_str,
            content,
            amount,
            type_,
            ""
        ])

        reply = f"{content} {amount}円 登録 👍（ID:{new_id}）"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    except:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="入力形式が違うよ！"))