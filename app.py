import requests
import time
import os
import threading
import http.server
import socketserver

# ================== НАСТРОЙКИ ==================
TOKEN = os.environ.get("BOT_TOKEN", "8918941174:AAGcBEBBMx88GAa6XGuqmjLLuSV136HuCOw")
SUBGRAM_API_KEY = os.environ.get("SUBGRAM_API_KEY", "0ee6cf29c3f3f9279eadcae83f8636187bd2dd5ee211528e3ad0a22f89aa73c4")
API = "https://api.telegram.org/bot" + TOKEN
BASE_REWARD = 0.5

# Временное хранилище (пока без Aiven)
local_db = {}

def get_user(uid):
    if uid not in local_db:
        local_db[uid] = {"balance": 0.0}
    return local_db[uid]

def update_balance(uid, amount):
    u = get_user(uid)
    u["balance"] = u.get("balance", 0.0) + amount

# ================== SUBGRAM API (РЕАЛЬНЫЙ) ==================
def subgram_get_sponsors(uid, chat_id):
    try:
        r = requests.post(
            "https://api.subgram.org/get-sponsors",
            headers={"Auth": SUBGRAM_API_KEY},
            json={"user_id": uid, "chat_id": chat_id},
            timeout=15
        )
        return r.json()
    except Exception as e:
        print("SubGram error:", e)
        return {"status": "error"}

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

def task_menu():
    return kb([
        [("✅ Проверить", "check"), ("⏭ Пропустить", "skip")]
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

# ================== ЗАПУСК ==================
print("Бот запущен (SubGram Real API)!")
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

                # --- ЗАРАБОТАТЬ / ПРОПУСТИТЬ (запрос нового задания) ---
                if act == "earn" or act == "skip":
                    answer_cb(cb["id"], "🔄 Проверяю...")
                    data = subgram_get_sponsors(uid, chat_id)
                    status = data.get("status")

                    if status == "ok":
                        update_balance(uid, BASE_REWARD)
                        send(chat_id, f"✅ Задание выполнено!\n💰 Ты получил {BASE_REWARD} ⭐", main_menu())
                    elif status == "warning":
                        send(chat_id, "📌 Подпишись на канал (он пришёл выше) и жми «Проверить»!", task_menu())
                    else:
                        send(chat_id, "😴 Каналов больше нет. Приходи через час!", main_menu())

                # --- ПРОВЕРИТЬ ПОДПИСКУ ---
                elif act == "check":
                    answer_cb(cb["id"], "🔄 Проверяю подписку...")
                    data = subgram_get_sponsors(uid, chat_id)
                    status = data.get("status")

                    if status == "ok":
                        update_balance(uid, BASE_REWARD)
                        send(chat_id, f"✅ Задание выполнено!\n💰 Ты получил {BASE_REWARD} ⭐", main_menu())
                    elif status == "warning":
                        send(chat_id, "❌ Ты не подписался! Подпишись и попробуй снова.", task_menu())
                    else:
                        send(chat_id, "😴 Каналов больше нет. Приходи через час!", main_menu())

                # --- МАГАЗИН ---
                elif act == "spend":
                    answer_cb(cb["id"])
                    rows = []
                    for gift_name, cost in GIFTS.items():
                        rows.append([{"text": f"{gift_name} — {cost}⭐", "callback_data": f"buy_{cost}"}])
                    rows.append([{"text": "⬅ Назад", "callback_data": "back"}])
                    send(chat_id, f"🎁 Магазин\n💰 Баланс: {balance:.1f} ⭐", {"inline_keyboard": rows})

                elif act.startswith("buy_"):
                    cost = float(act.split("_")[1])
                    if balance >= cost:
                        update_balance(uid, -cost)
                        # ЗАГЛУШКА ДЛЯ ПОДАРКОВ (пока не подключим sendGift)
                        send(chat_id, f"🎉 Подарок отправлен!\nОстаток: {balance - cost:.1f} ⭐", main_menu())
                    else:
                        answer_cb(cb["id"], "❌ Не хватает звёзд!", True)

                elif act == "profile":
                    answer_cb(cb["id"])
                    send(chat_id, f"👤 Твой ID: {uid}\n💰 Баланс: {balance:.1f} ⭐", main_menu())

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
                send(chat_id, "👋 Привет! Зарабатывай звёзды и покупай подарки.", main_menu())

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(3)
