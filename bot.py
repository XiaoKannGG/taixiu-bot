import telebot
import random
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
import time
from collections import defaultdict
import threading

# Khởi tạo bot với token của bạn
bot = telebot.TeleBot("7755493544:AAHhJld78NotMTwGdySlOuVmJRq2UEVnGFE")
ADMIN_ID = 5319454673

# Thông tin ngân hàng nạp tiền
BANK_INFO = """
💳 **Thông tin nạp tiền**:
- Ngân hàng: BIDV - Ngân hàng Thương mại cổ phần Đầu tư và Phát triển Việt Nam
- Số tài khoản: 8843677213
- Chủ tài khoản: LY KHAC TRUONG
- Nội dung chuyển khoản: NAP {user_id}
Vui lòng chuyển khoản đúng nội dung để hệ thống tự động cộng tiền!
"""

# Thông tin hỗ trợ
SUPPORT_INFO = """
MỌI CHI TIẾT VÀ THẮC MẮC VUI LÒNG LIÊN HỆ @Xiao_KanGG để được hỗ trợ,  
THỜI GIAN HỖ TRỢ TỪ 9:00 SÁNG ĐẾN 11:30 PHÚT TỐI,  
VUI LÒNG VÀO THẲNG VẤN ĐỀ CHÍNH KHÔNG VÒNG VO XIN CẢM ƠN
"""

# Tỷ lệ trả thưởng Sicbo cho cược tổng
SICBO_TOTAL_PAYOUT = {
    4: 50, 17: 50,
    5: 18, 16: 18,
    6: 14, 15: 14,
    7: 12, 14: 12,
    8: 8, 13: 8,
    9: 6, 10: 6, 11: 6, 12: 6
}

# Kết nối database
conn = sqlite3.connect('taixiu.db', check_same_thread=False)

# Tạo bảng nếu chưa tồn tại
with conn:
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY, 
                 balance REAL DEFAULT 0,
                 username TEXT,
                 bank_info TEXT DEFAULT NULL,
                 win_streak INTEGER DEFAULT 0,
                 rigged INTEGER DEFAULT 0)''')
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

# Biến lưu cược tạm thời và thời gian chờ
pending_bets = defaultdict(list)  # {user_id: [(bet_type, bet_value, amount), ...]}
bet_timeout = 5  # Thời gian chờ cược (giây)
timers = {}  # {user_id: threading.Timer}

# Menu nút bấm cố định
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🎲 Chơi tài xỉu"), KeyboardButton("💰 Nạp tiền"))
    markup.row(KeyboardButton("🏧 Rút tiền"), KeyboardButton("📊 Kiểm tra tài khoản"))
    markup.row(KeyboardButton("📜 Lịch sử cược"), KeyboardButton("🧾 Lịch sử giao dịch"))
    markup.row(KeyboardButton("🏦 Xác minh tài khoản"), KeyboardButton("🔮 Soi cầu"))
    markup.row(KeyboardButton("📞 Hỗ trợ"))
    return markup

# Lệnh /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Không có username"
    with conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, win_streak, rigged) VALUES (?, ?, 0, 0)", (user_id, username))
    welcome_msg = """Chào Mừng Bạn Đến Tài Xỉu 789 trên Telegram By XiaoKanGG
Chọn chức năng trong menu nút bấm dưới đây!

🎲 **Các cửa cược và tỷ lệ trả thưởng**:
- **Tài/Xỉu**: /tai, /xiu [số tiền] (VD: /tai 10000)
  + Thắng: 1:1 (Cược 10.000 thắng 10.000, nhận tổng 20.000)
- **Chẵn/Lẻ**: /chan, /le [số tiền] (VD: /chan 10000)
  + Thắng: 1:1 (Cược 10.000 thắng 10.000, nhận tổng 20.000)
- **Tổng điểm**: /total [4-17] [số tiền] (VD: /total 10 10000)
  + 4 hoặc 17: 1:50 (Cược 10.000 thắng 500.000)
  + 5 hoặc 16: 1:18 (Cược 10.000 thắng 180.000)
  + 6 hoặc 15: 1:14 (Cược 10.000 thắng 140.000)
  + 7 hoặc 14: 1:12 (Cược 10.000 thắng 120.000)
  + 8 hoặc 13: 1:8 (Cược 10.000 thắng 80.000)
  + 9, 10, 11, 12: 1:6 (Cược 10.000 thắng 60.000)
- **Bão**: /bao [1-6] [số tiền] (VD: /bao 1 10000)
  + 1-1-1: 1:8 (Cược 10.000 thắng 80.000)
  + 2-2-2 đến 6-6-6: 1:150 (Cược 10.000 thắng 1.500.000)

**Lưu ý**: Bạn có thể cược nhiều cửa cùng lúc (VD: /tai 10000, /le 10000, /bao 1 10000). Bot sẽ chờ 5 giây để gom cược, rồi tung xúc xắc 1 lần duy nhất!
Chúc bạn chơi vui và thắng lớn!"""
    bot.reply_to(message, welcome_msg, reply_markup=main_menu())

# Xử lý các lệnh từ nút bấm
@bot.message_handler(func=lambda message: message.text in ["🎲 Chơi tài xỉu", "💰 Nạp tiền", "🏧 Rút tiền", "📊 Kiểm tra tài khoản", "📜 Lịch sử cược", "🧾 Lịch sử giao dịch", "🏦 Xác minh tài khoản", "🔮 Soi cầu", "📞 Hỗ trợ"])
def handle_menu(message):
    user_id = message.from_user.id
    if message.text == "🎲 Chơi tài xỉu":
        bot.reply_to(message, """Chọn cửa cược (có thể cược nhiều cửa cùng lúc):

- **Tài/Xỉu**: /tai, /xiu [số tiền] (VD: /tai 10000)
  + Tỷ lệ 1:1 (Cược 10.000 thắng 10.000)
- **Chẵn/Lẻ**: /chan, /le [số tiền] (VD: /chan 10000)
  + Tỷ lệ 1:1 (Cược 10.000 thắng 10.000)
- **Tổng điểm**: /total [4-17] [số tiền] (VD: /total 10 10000)
  + 4, 17: 1:50 | 5, 16: 1:18 | 6, 15: 1:14 | 7, 14: 1:12 | 8, 13: 1:8 | 9-12: 1:6
- **Bão**: /bao [1-6] [số tiền] (VD: /bao 1 10000)
  + 1-1-1: 1:8 | 2-2-2 đến 6-6-6: 1:150

**Lưu ý**: Gửi các lệnh cược liên tiếp trong 5 giây (VD: /tai 10000, /le 10000, /bao 1 10000), bot sẽ gom lại và tung xúc xắc 1 lần duy nhất!""")
    elif message.text == "💰 Nạp tiền":
        bot.reply_to(message, BANK_INFO.format(user_id=user_id) + "\n**Lưu ý**: Số tiền nạp tối thiểu là 10,000 VND!")
    elif message.text == "🏧 Rút tiền":
        bot.reply_to(message, "Gửi số tiền muốn rút\nVí dụ: /rut 200000\n**Lưu ý**: Số tiền rút tối thiểu là 200,000 VND!")
    elif message.text == "📊 Kiểm tra tài khoản":
        with conn:
            c = conn.cursor()
            c.execute("SELECT balance, bank_info FROM users WHERE user_id=?", (user_id,))
            result = c.fetchone()
        balance = result[0] if result else 0
        bank_info = result[1] if result else None
        if bank_info:
            response = f"📊 **Thông tin tài khoản**:\n- Số dư hiện tại: {balance:,} VNĐ\n- Tài khoản ngân hàng: {bank_info}"
        else:
            response = f"📊 **Thông tin tài khoản**:\n- Số dư hiện tại: {balance:,} VNĐ\n- Bạn chưa xác minh tài khoản ngân hàng!"
        bot.reply_to(message, response)
    elif message.text == "📜 Lịch sử cược":
        with conn:
            c = conn.cursor()
            c.execute("SELECT bet, result, amount, timestamp FROM bet_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 50", (user_id,))
            history = c.fetchall()
        if history:
            response = "📜 **Lịch sử cược (50 lần gần nhất)**:\n"
            for bet, result, amount, timestamp in history:
                response += f"- {timestamp}: Đặt {bet}, Kết quả: {result}, {amount:,} VNĐ\n"
        else:
            response = "Bạn chưa có lịch sử cược nào!"
        bot.reply_to(message, response)
    elif message.text == "🧾 Lịch sử giao dịch":
        with conn:
            c = conn.cursor()
            c.execute("SELECT type, amount, status, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT 50", (user_id,))
            history = c.fetchall()
        if history:
            response = "🧾 **Lịch sử giao dịch (50 lần gần nhất)**:\n"
            for type, amount, status, timestamp in history:
                response += f"- {timestamp}: {type}, {amount:,} VNĐ, Trạng thái: {status}\n"
        else:
            response = "Bạn chưa có lịch sử giao dịch nào!"
        bot.reply_to(message, response)
    elif message.text == "🏦 Xác minh tài khoản":
        with conn:
            c = conn.cursor()
            c.execute("SELECT bank_info FROM users WHERE user_id=?", (user_id,))
            bank_info = c.fetchone()[0]
        if bank_info:
            bot.reply_to(message, f"Tài khoản ngân hàng của bạn đã được xác minh: {bank_info}\nNếu muốn thay đổi, vui lòng liên hệ @Xiao_KanGG để được hỗ trợ!")
        else:
            bot.reply_to(message, "Vui lòng gửi thông tin tài khoản ngân hàng để xác minh:\nVí dụ: /verify [Tên ngân hàng] [Số tài khoản] [Tên chủ tài khoản]")
    elif message.text == "🔮 Soi cầu":
        with conn:
            c = conn.cursor()
            c.execute("SELECT result, timestamp FROM bet_history ORDER BY timestamp DESC LIMIT 20")
            history = c.fetchall()
        if history:
            response = "🔮 **Soi cầu (20 kết quả gần nhất toàn hệ thống)**:\n💙 = Xỉu | ❤️ = Tài\n\n"
            for result, timestamp in history:
                icon = "💙" if "Xỉu" in result else "❤️"
                response += f"- {timestamp}: {icon}\n"
            response += "\n**Chú thích**: Dựa vào kết quả trên để dự đoán lần cược tiếp theo. Chúc bạn may mắn!"
        else:
            response = "Chưa có dữ liệu để soi cầu!"
        bot.reply_to(message, response)
    elif message.text == "📞 Hỗ trợ":
        bot.reply_to(message, SUPPORT_INFO)

# Hàm xử lý cược chồng với 1 lần tung xúc xắc
def process_bets(user_id, chat_id):
    if user_id not in pending_bets or not pending_bets[user_id]:
        return
    
    bets = pending_bets[user_id]
    total_bet_amount = sum(bet[2] for bet in bets)
    
    with conn:
        c = conn.cursor()
        c.execute("SELECT balance, win_streak, rigged FROM users WHERE user_id=?", (user_id,))
        balance, win_streak, rigged = c.fetchone()
    
    if balance < total_bet_amount:
        bot.send_message(chat_id, "Số dư không đủ để đặt cược tất cả các cửa!")
        del pending_bets[user_id]
        return
    
    bot.send_message(chat_id, "Đang tung xúc xắc...")
    dice_results = []
    if rigged:  # Can thiệp để thua
        for bet_type, bet_value, _ in bets:
            if bet_type == "tai":
                dice_results = [1, 1, 1]  # Tổng 3 (Xỉu)
                break
            elif bet_type == "xiu":
                dice_results = [6, 6, 6]  # Tổng 18 (Tài)
                break
            elif bet_type == "chan":
                dice_results = [1, 1, 1]  # Tổng 3 (Lẻ)
                break
            elif bet_type == "le":
                dice_results = [2, 2, 2]  # Tổng 6 (Chẵn)
                break
            elif bet_type == "total":
                dice_results = [1, 1, 1] if bet_value > 3 else [6, 6, 6]  # Tránh tổng cược
                break
            elif bet_type == "bao":
                dice_results = [1, 2, 3]  # Không phải Bão
                break
    else:
        for i in range(3):
            dice_msg = bot.send_dice(chat_id)
            dice_value = dice_msg.dice.value
            dice_results.append(dice_value)
            time.sleep(2)
    
    total = sum(dice_results)
    is_even = total % 2 == 0
    result_text = f"Tổng: {total} - {'Tài' if total >= 11 else 'Xỉu'} {'(Chẵn)' if is_even else '(Lẻ)'}"
    response = f"Kết quả: {dice_results[0]}-{dice_results[1]}-{dice_results[2]}\n{result_text}\n"
    total_winnings = 0
    new_win_streak = win_streak
    
    with conn:
        c = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for bet_type, bet_value, amount in bets:
            winnings = -amount  # Mặc định thua
            
            if bet_type == "tai" and total >= 11:
                winnings = amount
                response += f"- Tài: Thắng {winnings:,} VNĐ (1:1)\n"
            elif bet_type == "xiu" and total < 11:
                winnings = amount
                response += f"- Xỉu: Thắng {winnings:,} VNĐ (1:1)\n"
            elif bet_type == "chan" and is_even:
                winnings = amount
                response += f"- Chẵn: Thắng {winnings:,} VNĐ (1:1)\n"
            elif bet_type == "le" and not is_even:
                winnings = amount
                response += f"- Lẻ: Thắng {winnings:,} VNĐ (1:1)\n"
            elif bet_type == "total" and total == bet_value:
                payout = SICBO_TOTAL_PAYOUT.get(total, 0)
                winnings = amount * payout
                response += f"- Tổng {bet_value}: Thắng {winnings:,} VNĐ (1:{payout})\n"
            elif bet_type == "bao" and dice_results[0] == dice_results[1] == dice_results[2] == bet_value:
                payout = 8 if bet_value == 1 else 150
                winnings = amount * payout
                response += f"- Bão {bet_value}: Thắng {winnings:,} VNĐ (1:{payout})\n"
            else:
                response += f"- {bet_type.capitalize()} {' ' + str(bet_value) if bet_type in ['total', 'bao'] else ''}: Thua {amount:,} VNĐ\n"
            
            total_winnings += winnings
            c.execute("INSERT INTO bet_history (user_id, bet, result, amount, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (user_id, f"{bet_type.capitalize()} {' ' + str(bet_value) if bet_type in ['total', 'bao'] else ''}", result_text, winnings, timestamp))
        
        if total_winnings > 0:
            new_win_streak += 1
            if new_win_streak >= 5:
                bot.send_message(ADMIN_ID, f"Người chơi {user_id} (@{c.execute('SELECT username FROM users WHERE user_id=?', (user_id,)).fetchone()[0]}) thắng {new_win_streak} trận liên tục!")
        else:
            new_win_streak = 0
        
        c.execute("UPDATE users SET balance = balance + ?, win_streak = ?, rigged = ? WHERE user_id=?", 
                  (total_winnings, new_win_streak, 0 if rigged else rigged, user_id))
    
    response += f"\nTổng tiền thắng/thua: {total_winnings:,} VNĐ"
    bot.send_message(chat_id, response, reply_markup=main_menu())
    del pending_bets[user_id]

# Hàm đặt cược và lên lịch xử lý
def schedule_bet_processing(user_id, chat_id):
    if user_id in timers:
        timers[user_id].cancel()  # Hủy timer cũ nếu có
    timer = threading.Timer(bet_timeout, process_bets, args=(user_id, chat_id))
    timers[user_id] = timer
    timer.start()

# Chơi tài xỉu, chẵn lẻ
@bot.message_handler(commands=['tai', 'xiu', 'chan', 'le'])
def play_game(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    bet_type = message.text.split()[0][1:]
    try:
        amount = float(message.text.split()[1])
        if amount <= 0:
            bot.reply_to(message, "Số tiền cược phải lớn hơn 0!")
            return
        
        pending_bets[user_id].append((bet_type, None, amount))
        bot.reply_to(message, f"Đã thêm cược: {bet_type.capitalize()} {amount:,} VNĐ. Gửi thêm cược trong {bet_timeout} giây, bot sẽ tung xúc xắc 1 lần!")
        schedule_bet_processing(user_id, chat_id)
    except IndexError:
        bot.reply_to(message, f"Vui lòng nhập đúng định dạng: /{bet_type} [số tiền] (VD: /{bet_type} 10000)")
    except ValueError:
        bot.reply_to(message, "Số tiền phải là một số hợp lệ!")

# Cược tổng điểm
@bot.message_handler(commands=['total'])
def play_total(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Sai định dạng! Sử dụng: /total [4-17] [số tiền] (VD: /total 10 10000)")
            return
        total_bet = int(args[1])
        amount = float(args[2])
        if total_bet < 4 or total_bet > 17:
            bot.reply_to(message, "Tổng điểm phải từ 4 đến 17!")
            return
        if amount <= 0:
            bot.reply_to(message, "Số tiền cược phải lớn hơn 0!")
            return
        
        pending_bets[user_id].append(("total", total_bet, amount))
        bot.reply_to(message, f"Đã thêm cược: Tổng {total_bet} {amount:,} VNĐ. Gửi thêm cược trong {bet_timeout} giây, bot sẽ tung xúc xắc 1 lần!")
        schedule_bet_processing(user_id, chat_id)
    except ValueError:
        bot.reply_to(message, "Tổng điểm và số tiền phải là số hợp lệ! VD: /total 10 10000")

# Cược Bão
@bot.message_handler(commands=['bao'])
def play_bao(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Sai định dạng! Sử dụng: /bao [1-6] [số tiền] (VD: /bao 1 10000)")
            return
        bao_bet = int(args[1])
        amount = float(args[2])
        if bao_bet < 1 or bao_bet > 6:
            bot.reply_to(message, "Số Bão phải từ 1 đến 6!")
            return
        if amount <= 0:
            bot.reply_to(message, "Số tiền cược phải lớn hơn 0!")
            return
        
        pending_bets[user_id].append(("bao", bao_bet, amount))
        bot.reply_to(message, f"Đã thêm cược: Bão {bao_bet} {amount:,} VNĐ. Gửi thêm cược trong {bet_timeout} giây, bot sẽ tung xúc xắc 1 lần!")
        schedule_bet_processing(user_id, chat_id)
    except ValueError:
        bot.reply_to(message, "Số Bão và số tiền phải là số hợp lệ! VD: /bao 1 10000")

# Nạp tiền
@bot.message_handler(commands=['nap'])
def deposit(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text.split()[1])
        if amount < 10000:
            bot.reply_to(message, "Số tiền nạp tối thiểu là 10,000 VND!")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            c = conn.cursor()
            c.execute("INSERT INTO transactions (user_id, type, amount, timestamp) VALUES (?, ?, ?, ?)",
                      (user_id, "Nạp", amount, timestamp))
        bot.reply_to(message, f"Yêu cầu nạp tiền đã được gửi đến admin. Vui lòng chuyển khoản theo thông tin:\n{BANK_INFO.format(user_id=user_id)}")
        bot.send_message(ADMIN_ID, f"Người dùng {user_id} (@{message.from_user.username}) yêu cầu nạp {amount:,} VNĐ\nThời gian: {timestamp}")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /nap [số tiền] (Tối thiểu 10,000 VND)")
    except ValueError:
        bot.reply_to(message, "Số tiền phải là một số hợp lệ!")

# Rút tiền
@bot.message_handler(commands=['rut'])
def withdraw(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text.split()[1])
        if amount < 200000:
            bot.reply_to(message, "Số tiền rút tối thiểu là 200,000 VND!")
            return
        with conn:
            c = conn.cursor()
            c.execute("SELECT balance, bank_info FROM users WHERE user_id=?", (user_id,))
            result = c.fetchone()
            balance, bank_info = result if result else (0, None)
        
        if balance < amount:
            bot.reply_to(message, "Số dư không đủ để rút!")
            return
        if not bank_info:
            bot.reply_to(message, "Bạn chưa xác minh tài khoản ngân hàng! Sử dụng lệnh: /verify [Tên ngân hàng] [Số tài khoản] [Tên chủ tài khoản]")
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
            c.execute("INSERT INTO transactions (user_id, type, amount, timestamp) VALUES (?, ?, ?, ?)",
                      (user_id, "Rút", amount, timestamp))
        
        bot.reply_to(message, f"Yêu cầu rút {amount:,} VNĐ đã được gửi đến admin. Số dư đã bị trừ, vui lòng chờ xác nhận!")
        bot.send_message(ADMIN_ID, f"Người dùng {user_id} (@{message.from_user.username}) yêu cầu rút {amount:,} VNĐ\nTài khoản: {bank_info}\nThời gian: {timestamp}")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /rut [số tiền] (Tối thiểu 200,000 VND)")
    except ValueError:
        bot.reply_to(message, "Số tiền phải là một số hợp lệ!")

# Xác minh tài khoản ngân hàng
@bot.message_handler(commands=['verify'])
def verify_account(message):
    user_id = message.from_user.id
    with conn:
        c = conn.cursor()
        c.execute("SELECT bank_info FROM users WHERE user_id=?", (user_id,))
        bank_info = c.fetchone()[0]
    
    if bank_info:
        bot.reply_to(message, f"Tài khoản ngân hàng của bạn đã được xác minh: {bank_info}\nNếu muốn thay đổi, vui lòng liên hệ @Xiao_KanGG để được hỗ trợ!")
        return
    
    try:
        args = message.text.split(maxsplit=1)[1]
        if not args:
            bot.reply_to(message, "Vui lòng cung cấp thông tin tài khoản!\nVí dụ: /verify Vietcombank 123456789 NGUYEN VAN A")
            return
        with conn:
            c = conn.cursor()
            c.execute("UPDATE users SET bank_info = ? WHERE user_id=?", (args, user_id))
        bot.reply_to(message, f"Tài khoản ngân hàng của bạn đã được xác minh: {args}\nBây giờ bạn có thể rút tiền.\nDùng /balance hoặc nút 'Kiểm tra tài khoản' để xem thông tin!")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập đúng định dạng: /verify [Tên ngân hàng] [Số tài khoản] [Tên chủ tài khoản]")

# Thay đổi tài khoản ngân hàng (chỉ admin)
@bot.message_handler(commands=['changebank'])
def change_bank(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này!")
        return
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            bot.reply_to(message, "Sai cú pháp! Sử dụng: /changebank [user_id] [Tên ngân hàng] [Số tài khoản] [Tên chủ tài khoản]")
            return
        target_user_id = int(args[1])
        new_bank_info = args[2]
        with conn:
            c = conn.cursor()
            c.execute("UPDATE users SET bank_info = ? WHERE user_id=?", (new_bank_info, target_user_id))
            updated = c.rowcount
        if updated > 0:
            bot.reply_to(message, f"Đã cập nhật tài khoản ngân hàng cho {target_user_id}: {new_bank_info}")
            bot.send_message(target_user_id, f"Tài khoản ngân hàng của bạn đã được Admin cập nhật: {new_bank_info}")
        else:
            bot.reply_to(message, f"Không tìm thấy người dùng {target_user_id}!")
    except ValueError:
        bot.reply_to(message, "User_id phải là số hợp lệ! Sử dụng: /changebank [user_id] [Tên ngân hàng] [Số tài khoản] [Tên chủ tài khoản]")

# Can thiệp kết quả (chỉ admin)
@bot.message_handler(commands=['rig'])
def rig_game(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này!")
        return
    try:
        args = message.text.split()
        if len(args) != 3 or args[2] not in ["on", "off"]:
            bot.reply_to(message, "Sai cú pháp! Sử dụng: /rig [user_id] [on/off]")
            return
        target_user_id = int(args[1])
        rig_status = 1 if args[2] == "on" else 0
        with conn:
            c = conn.cursor()
            c.execute("UPDATE users SET rigged = ? WHERE user_id=?", (rig_status, target_user_id))
            updated = c.rowcount
        if updated > 0:
            bot.reply_to(message, f"Đã {'bật' if rig_status else 'tắt'} chế độ can thiệp cho {target_user_id}!")
        else:
            bot.reply_to(message, f"Không tìm thấy người dùng {target_user_id}!")
    except ValueError:
        bot.reply_to(message, "User_id phải là số hợp lệ! Sử dụng: /rig [user_id] [on/off]")

# Soi cầu
@bot.message_handler(commands=['soicau'])
def soi_cau(message):
    with conn:
        c = conn.cursor()
        c.execute("SELECT result, timestamp FROM bet_history ORDER BY timestamp DESC LIMIT 20")
        history = c.fetchall()
    if history:
        response = "🔮 **Soi cầu (20 kết quả gần nhất toàn hệ thống)**:\n💙 = Xỉu | ❤️ = Tài\n\n"
        for result, timestamp in history:
            icon = "💙" if "Xỉu" in result else "❤️"
            response += f"- {timestamp}: {icon}\n"
        response += "\n**Chú thích**: Dựa vào kết quả trên để dự đoán lần cược tiếp theo. Chúc bạn may mắn!"
    else:
        response = "Chưa có dữ liệu để soi cầu!"
    bot.reply_to(message, response)

# Xem số dư và thông tin tài khoản
@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = message.from_user.id
    with conn:
        c = conn.cursor()
        c.execute("SELECT balance, bank_info FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
    balance = result[0] if result else 0
    bank_info = result[1] if result else None
    if bank_info:
        response = f"📊 **Thông tin tài khoản**:\n- Số dư hiện tại: {balance:,} VNĐ\n- Tài khoản ngân hàng: {bank_info}"
    else:
        response = f"📊 **Thông tin tài khoản**:\n- Số dư hiện tại: {balance:,} VNĐ\n- Bạn chưa xác minh tài khoản ngân hàng!"
    bot.reply_to(message, response)

# Xem lịch sử giao dịch
@bot.message_handler(commands=['transaction_history'])
def transaction_history(message):
    user_id = message.from_user.id
    with conn:
        c = conn.cursor()
        c.execute("SELECT type, amount, status, timestamp FROM transactions WHERE user_id=? ORDER BY timestamp DESC LIMIT 50", (user_id,))
        history = c.fetchall()
    if history:
        response = "🧾 **Lịch sử giao dịch (50 lần gần nhất)**:\n"
        for type, amount, status, timestamp in history:
            response += f"- {timestamp}: {type}, {amount:,} VNĐ, Trạng thái: {status}\n"
    else:
        response = "Bạn chưa có lịch sử giao dịch nào!"
    bot.reply_to(message, response)

# Xem lịch sử cược
@bot.message_handler(commands=['bet_history'])
def bet_history(message):
    user_id = message.from_user.id
    with conn:
        c = conn.cursor()
        c.execute("SELECT bet, result, amount, timestamp FROM bet_history WHERE user_id=? ORDER BY timestamp DESC LIMIT 50", (user_id,))
        history = c.fetchall()
    if history:
        response = "📜 **Lịch sử cược (50 lần gần nhất)**:\n"
        for bet, result, amount, timestamp in history:
            response += f"- {timestamp}: Đặt {bet}, Kết quả: {result}, {amount:,} VNĐ\n"
    else:
        response = "Bạn chưa có lịch sử cược nào!"
    bot.reply_to(message, response)

# Hỗ trợ
@bot.message_handler(commands=['support'])
def support(message):
    bot.reply_to(message, SUPPORT_INFO)

# Lệnh cộng tiền (chỉ admin)
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
        with conn:
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_user_id))
            c.execute("UPDATE transactions SET status = 'completed' WHERE user_id=? AND type='Nạp' AND amount=? AND status='pending'", 
                      (target_user_id, amount))
        bot.reply_to(message, f"Đã cộng {amount:,} VNĐ vào tài khoản {target_user_id}!")
        bot.send_message(target_user_id, f"Bạn đã được cộng {amount:,} VNĐ vào tài khoản!")
    except ValueError:
        bot.reply_to(message, "User_id và số tiền phải là số hợp lệ! Sử dụng: /addmoney [user_id] [số tiền]")

# Lệnh xác nhận rút tiền (chỉ admin)
@bot.message_handler(commands=['confirm_withdraw'])
def confirm_withdraw(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này!")
        return
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Sai cú pháp! Sử dụng: /confirm_withdraw [user_id] [số tiền]")
            return
        target_user_id = int(args[1])
        amount = float(args[2])
        with conn:
            c = conn.cursor()
            c.execute("UPDATE transactions SET status = 'completed' WHERE user_id=? AND type='Rút' AND amount=? AND status='pending'",
                      (target_user_id, amount))
            updated = c.rowcount
        if updated > 0:
            bot.reply_to(message, f"Đã xác nhận rút {amount:,} VNĐ cho người dùng {target_user_id}!")
            bot.send_message(target_user_id, f"Yêu cầu rút {amount:,} VNĐ của bạn đã được xác nhận thành công!")
        else:
            bot.reply_to(message, "Không tìm thấy yêu cầu rút tiền phù hợp để xác nhận!")
    except ValueError:
        bot.reply_to(message, "User_id và số tiền phải là số hợp lệ! Sử dụng: /confirm_withdraw [user_id] [số tiền]")

# Chạy bot
if __name__ == "__main__":
    print("Bot đang chạy...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Lỗi: {e}")
            time.sleep(5)