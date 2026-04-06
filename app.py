from flask import Flask, request, abort
import os
import datetime
import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== Google Sheets =====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("家計簿").sheet1

@app.route("/")
def home():
    return "OK"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

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
給料 +200000

【複数登録】
ランチ 800
カフェ 500

【確認】
今月 / 3月

【削除】
削除 1 3 5

【変更】
変更 1 1000 3 2000
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

            expense_lines = []
            income_lines = []

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

                    line = f"{id_}. {content} {amount:,}円"

                    if type_ == "収入":
                        income_lines.append(line)
                        total_in += amount
                    else:
                        expense_lines.append(line)
                        total_out += amount

            balance = total_in - total_out
            balance_text = f"+{balance:,}" if balance >= 0 else f"{balance:,}"

            msg = f"【{target_month}月】\n"
            msg += "\nー支出ー\n" + ("\n".join(expense_lines) if expense_lines else "なし")
            msg += "\n\nー収入ー\n" + ("\n".join(income_lines) if income_lines else "なし")
            msg += "\n\nー総計ー\n"
            msg += f"収入：{total_in:,}円\n"
            msg += f"支出：{total_out:,}円\n"
            msg += f"収支：{balance_text}円"

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="3月 の形式で入力してね"))
        return

    # ===== 複数削除 =====
    if text.startswith("削除"):
        try:
            ids = text.split()[1:]
            data = sheet.get_all_values()

            for i in reversed(range(len(data))):
                if data[i] and data[i][0] in ids:
                    sheet.delete_rows(i + 1)

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="削除完了 👍"))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="削除 1 3 5 の形式で入力"))
        return

    # ===== 複数変更 =====
    if text.startswith("変更"):
        try:
            parts = text.split()[1:]

            if len(parts) % 2 != 0:
                raise Exception()

            data = sheet.get_all_values()

            for i in range(0, len(parts), 2):
                target_id = parts[i]
                new_amount = parts[i+1]

                for row_index, row in enumerate(data):
                    if row and row[0] == target_id:
                        sheet.update_cell(row_index + 1, 4, new_amount)

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="変更完了 👍"))
        except:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="変更 1 1000 3 2000"))
        return

    # ===== 複数登録 =====
    try:
        lines = text.split("\n")
        data = sheet.get_all_values()
        start_id = len(data)

        count = 0

        for line in lines:
            parts = line.split(" ")

            if len(parts) != 2:
                continue

            content = parts[0]
            amount = parts[1]

            if amount.startswith("+"):
                amount = amount.replace("+", "")
                type_ = "収入"
            else:
                type_ = "支出"

            if not amount.isdigit():
                continue

            sheet.append_row([
                str(start_id + count),
                str(today),
                content,
                amount,
                type_,
                ""
            ])

            count += 1

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{count}件登録 👍")
        )

    except:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="入力エラー")
        )