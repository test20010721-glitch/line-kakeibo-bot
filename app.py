from flask import Flask, request
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from linebot import LineBotApi
from linebot.models import TextSendMessage

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "U2U5Hvl/3BHttw0mipKvNcKaATJX52n2z0xi0q/x+Q09YlhfwNTaWU3v/zyz4qATqxKriUnEpFwmGodPZhogjK4iRJx12GCMGYxRNwQA/0nSf4JFSY7u5gR3kW+h06Yv4WqaW/kpFJLL31wLCLXFPgdB04t89/1O/w1cDnyilFU="
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
print("TOKEN:", LINE_CHANNEL_ACCESS_TOKEN)

# ===== Google Sheets =====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("家計簿").sheet1

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

@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json()
    event = body["events"][0]

    reply_token = event["replyToken"]
    text = event["message"]["text"]

    # ===== ヘルプ =====
    if text == "ヘルプ":
        line_bot_api.reply_message(reply_token, TextSendMessage(text=HELP))
        return "OK"

    # ===== 今月 =====
    if text == "今月":
        data = sheet.get_all_values()[1:]

        total = 0
        msg = "【一覧】\n"

        for i, row in enumerate(data):
            msg += f"{i+1}. {row[1]} {row[2]}円\n"
            if row[3] == "支出":
                total += int(row[2])

        msg += f"\n合計：{total}円"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=msg))
        return "OK"

    # ===== 削除 =====
    if text.startswith("削除"):
        num = int(text.split(" ")[1])
        sheet.delete_rows(num+1)
        line_bot_api.reply_message(reply_token, TextSendMessage(text="削除しました 👍"))
        return "OK"

    # ===== 変更 =====
    if text.startswith("変更"):
        parts = text.split(" ")
        num = int(parts[1])
        new_amount = parts[2]

        sheet.update_cell(num+1, 3, new_amount)

        line_bot_api.reply_message(reply_token, TextSendMessage(text="変更しました 👍"))
        return "OK"

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

        # 合計
        data = sheet.get_all_values()[1:]
        total = sum(int(r[2]) for r in data if r[3] == "支出")

        reply = f"{content} {amount}円 登録しました 👍\n\n今月の支出：{total}円"
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply))

    except:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=HELP))

    return "OK"

@app.route("/")
def home():
    return "OK"
