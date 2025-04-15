import logging
import gspread
import openai
import os
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# === CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHEET_URL = os.getenv("SHEET_URL")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# === KẾT NỐI GOOGLE SHEET ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDENTIALS_JSON), scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL)

# === OPENAI ===
openai.api_key = OPENAI_API_KEY

# === LƯU TRẠNG THÁI NGƯỜI DÙNG ===
user_state = {}

# === CHATGPT ===
def ask_chatgpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"⚠️ Lỗi kết nối GPT: {e}"

# === /START ===
def start(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("📝 ghi")],
        [KeyboardButton("📌 nhắc")],
        [KeyboardButton("💸 chi")],
        [KeyboardButton("🤖 chat")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("👋 Chào bạn! Đây là trợ lý ghi chú + AI. Hãy chọn lệnh bên dưới:", reply_markup=reply_markup)

# === HANDLE MESSAGE ===
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if text == "📝 ghi":
        user_state[user_id] = "ghi"
        update.message.reply_text("✏️ Nhập nội dung bạn muốn ghi chú:")
        return

    if text == "📌 nhắc":
        user_state[user_id] = "nhắc"
        update.message.reply_text("📌 Nhập việc - thời gian (VD: Gọi khách - 15h):")
        return

    if text == "💸 chi":
        user_state[user_id] = "chi"
        update.message.reply_text("💸 Nhập mục - tiền - đối tượng (VD: Mua cà phê - 25000 - Linh):")
        return

    if text == "🤖 chat":
        user_state[user_id] = "chat"
        update.message.reply_text("💬 Nhập câu hỏi bạn muốn ChatGPT trả lời:")
        return

    current = user_state.get(user_id)

    if current == "ghi":
        sheet.worksheet("Ghi chú").append_row([now, text])
        update.message.reply_text("✅ Đã lưu vào *Ghi chú*!")
        user_state[user_id] = None
        return

    if current == "nhắc":
        try:
            content = text.split("-")
            if len(content) < 2:
                raise ValueError("Không đủ dữ liệu")
            sheet.worksheet("Nhắc việc").append_row([c.strip() for c in content])
            update.message.reply_text("📌 Đã lưu vào *Nhắc việc*!")
        except:
            update.message.reply_text("❗ Sai cú pháp. VD: Gọi khách - 15h")
        user_state[user_id] = None
        return

    if current == "chi":
        try:
            content = text.split("-")
            if len(content) < 3:
                raise ValueError("Thiếu mục hoặc tiền hoặc đối tượng")
            row = [None, now] + [c.strip() for c in content]
            sheet.worksheet("Chi tiêu").append_row(row)
            update.message.reply_text("💸 Đã lưu vào *Chi tiêu*!")
        except:
            update.message.reply_text("❗ Sai cú pháp. VD: Mua cà phê - 25000 - Linh")
        user_state[user_id] = None
        return

    if current == "chat":
        reply = ask_chatgpt(text)
        update.message.reply_text(f"🤖 ChatGPT: {reply}")
        user_state[user_id] = None
        return

    update.message.reply_text("⚠️ Lệnh không hợp lệ. Hãy dùng đúng nút hoặc cú pháp:")

# === MAIN ===
def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
