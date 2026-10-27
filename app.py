import requests
import time
import os
import random
import threading
import http.server
import socketserver

# ================== НАСТРОЙКИ (БЕРУТСЯ ИЗ RENDER SECRETS) ==================
TOKEN = os.environ.get("BOT_TOKEN", "8918941174:AAGcBEBBMx88GAa6XGuqmjLLuSV136HuCOw")
# SUBGRAM_API_KEY и DATABASE_URL пока отключены, чтобы бот не падал при запуске
# Мы добавим их в следующем шаге, когда будем подключать Aiven

API = "https://api.telegram.org/bot" + TOKEN
BASE_REWARD = 0.5  # Награда за 1 задание

# Временное хранилище балансов (пока без Aiven)
local_db = {}

def get_user(uid):
    if uid not in local_db:
        local_db[uid] = {"balance": 0.0, "current_task": None}
    return local_db[uid]

def update_balance(uid, amount):
    u = get_user(uid)
    u["balance"] = u.get("balance", 0.0) + amount

# ================== SUBGRAM (ЗАГЛУШКИ) ==================
def subgram_get_task(uid):
    user = get_user(uid)
    if user.get("current_task"):
        return {"id": user["current_task"], "link": f"https://t.me/test_channel_{user['current_task']}", "title": f"Спонсор (продолжение)"}
    
    task_id = str(random.randint(1000, 9999))
    user["current_task"] = task_id
    return {"id": task_id, "link": f"https://t.me/test_channel_{task_id}", "title": f"Спонсор #{task_id}"}

def subgram_check_task(uid, task_id):
    return True 

# ================== TELEGRAM ==================
def api(method, payload):
    try:
        return requests.post(API + "/" + method, json=payload, timeout=15).json()
    except Exception as e:
        print(method, "error:", e)
        return {}

def send(chat_id, text, keyboard=None):
    p = {"chat_id": chat_id, "text": text}
    if keyboard: p["reply_markup"] = keyboard
    r = api("sendMessage", p)
    if not r.get("ok"): print("send FAIL:", r)
    return r

def answer_cb(cb_id, text="", alert=False):
    api("answerCallbackQuery", {"callback_query_id": cb_id, "text": text, "show_alert": alert})

def kb(rows):
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}

# ================== МЕНЮ ==================
def main_menu():
    return kb([
        [("💎 Заработать", "earn")],
        [("🎁 Потратить", "spend")],
        [("👤 Профиль", "profile")]
    ])

def task_menu(link, task_id):
    return kb([
        [("📢 Подписаться", link)],
        [("✅ Проверить", f"check_{task_id}"), ("⏭ Пропустить", f"skip_{task_id}")]
    ])

GIFTS = {
    "🌹 Роза": 10,
    "🧸 Мишка": 50,
    "🎂 Торт": 100,
    "👑 Корона": 500
}

# ================== ВЕБ-СЕРВЕР (ДЛЯ RENDER) ==================
def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is alive")
        def log_message(self, *args): pass
    try:
        with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print("Веб-сервер:", e)

# ================== ЛОГИКА ==================
def show_task(uid, chat_id):
    task = subgram_get_task(uid)
    text = f"📌 Новое задание\n\nПодпишись на канал:\n👉 {task['title']}\n\n💰 Награда: {BASE_REWARD} ⭐\n\n⚠️ Не отписывайся сразу, иначе проверка не пройдет!"
    send(chat_id, text, task_menu(task['link'], task['id']))

# ================== ЗАПУСК ==================
print("Бот запущен в режиме Заработка Звезд!")
threading.Thread(target=run_web_server, daemon=True).start()

offset = 0

while True:
    try:
        r = requests.get(API + "/getUpdates", params={"offset": offset, "timeout": 20}, timeout=25).json()
        if not r.get("ok"):
            time.sleep(2); continue

        for upd in r["result"]:
            offset = upd["update_id"] + 1

            cb = upd.get("callback_query")
            if cb:
                uid = cb["from"]["id"]
                chat_id = cb["message"]["chat"]["id"]
                act = cb["data"]

                user = get_user(uid)
                balance = float(user.get("balance", 0.0))

                if act == "earn":
                    answer_cb(cb["id"])
                    show_task(uid, chat_id)

                elif act.startswith("check_"):
                    task_id = act.split("_")[1]
                    answer_cb(cb["id"], "🔄 Проверяю подписку...")
                    
                    if subgram_check_task(uid, task_id):
                        update_balance(uid, BASE_REWARD)
                        user["current_task"] = None
                        send(chat_id, f"✅ Задание выполнено!\n💰 Ты получил {BASE_REWARD} ⭐", main_menu())
                    else:
                        send(chat_id, "❌ Ты не подписался на канал! Попробуй еще раз.", task_menu(f"https://t.me/test_channel_{task_id}", task_id))

                elif act.startswith("skip_"):
                    answer_cb(cb["id"], "⏭ Ищу другое задание...")
                    user["current_task"] = None
                    show_task(uid, chat_id)

                elif act == "spend":
                    answer_cb(cb["id"])
                    rows = []
                    for gift_name, cost in GIFTS.items():
                        rows.append([{"text": f"{gift_name} — {cost}⭐", "callback_data": f"buy_{cost}"}])
                    rows.append([{"text": "⬅ Назад", "callback_data": "back"}])
                    send(chat_id, f"🎁 Магазин подарков\n\nТвой баланс: {balance:.1f} ⭐\n\nВыбирай подарок, он придет в профиль Telegram!", {"inline_keyboard": rows})

                elif act.startswith("buy_"):
                    cost = float(act.split("_")[1])
                    if balance >= cost:
                        update_balance(uid, -cost)
                        send(chat_id, f"🎉 Подарок отправлен в твой профиль!\nОстаток: {balance - cost:.1f} ⭐", main_menu())
                    else:
                        answer_cb(cb["id"], "❌ Не хватает звезд!", True)

                elif act == "profile":
                    answer_cb(cb["id"])
                    send(chat_id, f"👤 Твой ID: {uid}\n💰 Баланс: {balance:.1f} ⭐\n\nЗарабатывай звезды и покупай подарки!", main_menu())

                elif act == "back":
                    answer_cb(cb["id"])
                    send(chat_id, "Главное меню:", main_menu())

                continue

            msg = upd.get("message")
            if not msg: continue
            chat_id = msg["chat"]["id"]
            uid = msg["from"]["id"]
            text = msg.get("text", "")

            if text.startswith("/start"):
                get_user(uid) 
                send(chat_id, "👋 Привет! Добро пожаловать в Звездный Заработок.\n\nЗдесь ты можешь выполнять задания и получать звезды, которые можно обменять на реальные подарки в твоем профиле Telegram.", main_menu())

    except Exception as e:
        print("Ошибка в цикле:", e)
        time.sleep(3)
