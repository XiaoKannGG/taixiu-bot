import telebot
import random
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import time

# Khởi tạo bot với token mới
bot = telebot.TeleBot("7755493544:AAHhJld78NotMTwGdySlOuVmJRq2UEVnGFE")
ADMIN_ID = 5319454673  # Giữ nguyên ID admin của bạn

# Thông tin ngân hàng
BANK_INFO = """
💳 **Thông tin nạp tiền**:
- Ngân hàng: BIDV - Ngân hàng Thương mại cổ phần Đầu tư và Phát triển Việt Nam
- Số tài khoản: 8843677213
- Chủ tài khoản: LY KHAC TRUONG
- Nội dung chuyển khoản: NAP {user_id}
Vui lòng chuyển khoản đúng nội dung để hệ thống tự động cộng tiền!
"""

# Kết nối database
conn = sqlite3.connect('taixiu.db', check_same_thread=False)
c = conn.cursor()

# Tạo bảng nếu chưa tồn tại
c.execute('''CREATE TABLE IF NOT EXISTS users (
             user_id INTEGER PRIMARY KEY, 
             balance REAL DEFAULT 0,
             username TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS bet_history (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER, 
             bet TEXT, 
             result TEXT, 
             amount REAL, 
             timestamp TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS transactions (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER, 
             type TEXT, 
             amount REAL, 
             status TEXT DEFAULT 'pending',
             timestamp TEXT)''')
conn.commit()

# Menu chính (nút inline)
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎲 Chơi tài xỉu", callback_data="play"),
               InlineKeyboardButton("💰 Nạp tiền", callback_data="deposit"))
    markup.row(InlineKeyboardButton("🏧 Rút tiền", callback_data="withdraw"),
               InlineKeyboardButton("📊 Kiểm tra tài khoản", callback_data="balance"))
    markup.row(InlineKeyboardButton("📜 Lịch sử cược", callback_data="bet_history"),
               InlineKeyboardButton("🧾 Lịch sử giao dịch", callback_data="transaction_history"))
    markup.row(InlineKeyboardButton("📞 Hỗ trợ", callback_data="support"))
    return markup

# Lệnh /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Không có username"
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    welcome_msg = "Chào Mừng Bạn Đến Tài Xỉu 789 trên Telegram By XiaoKanGG\nChọn chức năng bên dưới hoặc dùng lệnh trong menu!"
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

# Xử lý nút bấm inline
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if call.data == "play":
        bot.send_message(call.message.chat.id, "Chọn: Tài hoặc Xỉu\nVí dụ: /tai 10000 hoặc /xiu 10000")
    elif call.data == "deposit":
        bot.send_message(call.message.chat.id, BANK_INFO.format(user_id=user_id))
    elif call.data == "withdraw":
        bot.send_message(call.message.chat.id, "Gửi số tiền muốn rút\nVí dụ: /rut 50000")
    elif call.data == "balance":
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = c.fetchone()
        balance = balance[0] if balance else 0
        bot.send_message(call.message.chat.id, f"Số dư của bạn: {balance:,} VNĐ")
    elif call.data == "bet_history":
        c.execute("SELECT bet, result, amount, timestamp FROM bet_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 5", (user_id,))
        history = c.fetchall()
        if history:
            response = "📜 **Lịch sử cược (5 lần gần nhất)**:\n"
            for bet, result, amount, timestamp in history:
                response += f"- {timestamp}: Đặt {bet}, Kết quả: {result}, {amount:,} VNĐ\n"
        else:
            response = "Bạn chưa có lịch sử cược nào!"
        bot.send_message(call.message.chat.id, response)
    elif call.data == "transaction_history":
        c.execute("SELECT type, amount, status, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT 5", (user_id,))
        history = c.fetchall()
        if history:
            response = "🧾 **Lịch sử giao dịch (5 lần gần nhất)**:\n"
            for type, amount, status, timestamp in history:
                response += f"- {timestamp}: {type}, {amount:,} VNĐ, Trạng thái: {status}\n"
        else:
            response = "Bạn chưa có lịch sử giao dịch nào!"
        bot.send_message(call.message.chat.id, response)
    elif call.data == "support":
        bot.send_message(call.message.chat.id, "📞 Gửi yêu cầu hỗ trợ qua lệnh: /support [nội dung]")

# Chơi tài xỉu với hoạt ảnh xúc xắc
@bot.message_handler(commands=['tai', 'xiu'])
def play_game(message):
    user_id = message.from_user.id
    bet = message.text.split()[0][1:]  # Lấy "tai" hoặc "xiu"
    try:
        amount = float(message.text.split()[1])
        if amount <= 0:
            bot.reply_to(message, "Số tiền cược phải lớn hơn 0!")
            return
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = c.fetchone()
        if balance is None or balance[0] < amount:
            bot.reply_to(message, "Số dư không đủ!")
            return
        
        # Gửi từng hoạt ảnh xúc xắc
        bot.reply_to(message, "Đang tung xúc xắc...")
        dice_results = []
        for i in range(3):
            dice_msg = bot.send_dice(message.chat.id)
            dice_value = dice_msg.dice.value
            dice_results.append(dice_value)
            time.sleep(2)  # Chờ hoạt ảnh
        
        # Tính tổng và kết quả
        total = sum(dice_results)
        result = "Tài" if total >= 11 else "Xỉu"

        # Xử lý thắng thua
        if (bet == "tai" and total >= 11) or (bet == "xiu" and total < 11):
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
            bot.send_message(message.chat.id, f"Tổng: {total} - {result}\nBạn thắng {amount:,} VNĐ!")
            winnings = amount
        else:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
            bot.send_message(message.chat.id, f"Tổng: {total} - {result}\nBạn thua {amount:,} VNĐ!")
            winnings = -amount
        
        # Lưu lịch sử cược
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO bet_history (user_id, bet, result, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (user_id, bet.capitalize(), result, winnings, timestamp))
        conn.commit()

    except IndexError:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /tai [số tiền] hoặc /xiu [số tiền]")
    except ValueError:
        bot.reply_to(message, "Số tiền phải là một số hợp lệ!")
    except Exception as e:
        bot.reply_to(message, f"Lỗi không xác định: {str(e)}")

# Nạp tiền
@bot.message_handler(commands=['nap'])
def deposit(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text.split()[1])
        if amount <= 0:
            bot.reply_to(message, "Số tiền nạp phải lớn hơn 0!")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO transactions (user_id, type, amount, timestamp) VALUES (?, ?, ?, ?)",
                  (user_id, "Nạp", amount, timestamp))
        conn.commit()
        bot.reply_to(message, f"Yêu cầu nạp tiền đã được gửi đến admin. Vui lòng chuyển khoản theo thông tin:\n{BANK_INFO.format(user_id=user_id)}")
        bot.send_message(ADMIN_ID, f"Người dùng {user_id} (@{message.from_user.username}) yêu cầu nạp {amount:,} VNĐ\nThời gian: {timestamp}")
    except:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /nap [số tiền]")

# Rút tiền
@bot.message_handler(commands=['rut'])
def withdraw(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text.split()[1])
        if amount <= 0:
            bot.reply_to(message, "Số tiền rút phải lớn hơn 0!")
            return
        c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = c.fetchone()
        if balance is None or balance[0] < amount:
            bot.reply_to(message, "Số dư không đủ để rút!")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO transactions (user_id, type, amount, timestamp) VALUES (?, ?, ?, ?)",
                  (user_id, "Rút", amount, timestamp))
        conn.commit()
        bot.reply_to(message, "Yêu cầu rút tiền đã được gửi đến admin. Vui lòng chờ xác nhận!")
        bot.send_message(ADMIN_ID, f"Người dùng {user_id} (@{message.from_user.username}) yêu cầu rút {amount:,} VNĐ\nThời gian: {timestamp}")
    except:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /rut [số tiền]")

# Xem số dư
@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = message.from_user.id
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = c.fetchone()
    balance = balance[0] if balance else 0
    bot.reply_to(message, f"Số dư của bạn: {balance:,} VNĐ")

# Xem lịch sử giao dịch
@bot.message_handler(commands=['transaction_history'])
def transaction_history(message):
    user_id = message.from_user.id
    c.execute("SELECT type, amount, status, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT 5", (user_id,))
    history = c.fetchall()
    if history:
        response = "🧾 **Lịch sử giao dịch (5 lần gần nhất)**:\n"
        for type, amount, status, timestamp in history:
            response += f"- {timestamp}: {type}, {amount:,} VNĐ, Trạng thái: {status}\n"
    else:
        response = "Bạn chưa có lịch sử giao dịch nào!"
    bot.reply_to(message, response)

# Xem lịch sử cược
@bot.message_handler(commands=['bet_history'])
def bet_history(message):
    user_id = message.from_user.id
    c.execute("SELECT bet, result, amount, timestamp FROM bet_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 5", (user_id,))
    history = c.fetchall()
    if history:
        response = "📜 **Lịch sử cược (5 lần gần nhất)**:\n"
        for bet, result, amount, timestamp in history:
            response += f"- {timestamp}: Đặt {bet}, Kết quả: {result}, {amount:,} VNĐ\n"
    else:
        response = "Bạn chưa có lịch sử cược nào!"
    bot.reply_to(message, response)

# Liên hệ admin hỗ trợ
@bot.message_handler(commands=['support'])
def support(message):
    user_id = message.from_user.id
    try:
        content = " ".join(message.text.split()[1:])
        if not content:
            bot.reply_to(message, "Vui lòng nhập nội dung hỗ trợ!\nVí dụ: /support Tôi cần giúp đỡ về nạp tiền")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bot.reply_to(message, "Yêu cầu hỗ trợ đã được gửi đến admin. Vui lòng chờ phản hồi!")
        bot.send_message(ADMIN_ID, f"📞 Yêu cầu hỗ trợ từ {user_id} (@{message.from_user.username}):\nNội dung: {content}\nThời gian: {timestamp}")
    except:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /support [nội dung]")

# Lệnh cộng tiền cho tài khoản (chỉ admin)
@bot.message_handler(commands=['addmoney'])
def add_money(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này!")
        return
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Sai cú pháp! Sử dụng: /addmoney [user_id] [số tiền]")
            return
        target_user_id = int(args[1])
        amount = float(args[2])
        if amount <= 0:
            bot.reply_to(message, "Số tiền phải lớn hơn 0!")
            return
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_user_id))
        c.execute("UPDATE transactions SET status = 'completed' WHERE user_id=? AND type='Nạp' AND amount=? AND status='pending'", 
                  (target_user_id, amount))
        conn.commit()
        bot.reply_to(message, f"Đã cộng {amount:,} VNĐ vào tài khoản {target_user_id}!")
        bot.send_message(target_user_id, f"Bạn đã được cộng {amount:,} VNĐ vào tài khoản!")
    except ValueError:
        bot.reply_to(message, "User_id và số tiền phải là số hợp lệ! Sử dụng: /addmoney [user_id] [số tiền]")
    except Exception as e:
        bot.reply_to(message, f"Lỗi: {str(e)}. Sử dụng: /addmoney [user_id] [số tiền]")

# Chạy bot
if __name__ == "__main__":
    print("Bot đang chạy...")
    bot.polling(none_stop=True)