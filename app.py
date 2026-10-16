import requests
import time
import json
import os
import random
import threading
import http.server
import socketserver

TOKEN = ""
API = "https://api.telegram.org/bot" + TOKEN
SAVE_FILE = "secret_friend.json"
offset = 0

ADMIN_PASSWORD = "12345"
BOT_USERNAME = "Tajnij_dryg_bot"

users_reg = {}
чаты = {}

КОМПЛИМЕНТЫ = [
    "Ты сегодня просто огонь", "С тобой всегда весело", "Ты очень умный, не забывай об этом",
    "Твоя улыбка делает день лучше", "Ты классный друг, спасибо что ты есть",
    "Твоя энергия заражает всех вокруг", "Ты умеешь поддержать в нужный момент",
    "С тобой не страшно ничего", "Ты очень талантливый", "Твоё чувство юмора — топ",
    "Ты делаешь этот мир лучше", "С тобой время летит незаметно", "Ты настоящий друг",
    "Твоя доброта бесценна", "Ты вдохновляешь меня", "С тобой любое дело по плечу",
    "Ты очень отзывчивый", "Твоя поддержка много значит", "Ты классно выглядишь сегодня",
    "Ты всегда найдёшь нужные слова", "С тобой интересно болтать", "Ты очень честный",
    "Твоя искренность подкупает", "Ты заслуживаешь всего лучшего", "Ты очень стильный",
    "С тобой весело даже в дождь", "Ты настоящий лидер", "Твоя настойчивость впечатляет",
    "Ты умеешь мечтать", "Ты очень внимательный", "С тобой уютно молчать",
    "Ты умеешь слушать", "Твои идеи — огонь", "Ты творческая личность",
    "У тебя отличный вкус", "Ты очень терпеливый", "С тобой хочется дружить",
    "Ты надёжный, как скала", "Твоя улыбка заразительна", "Ты умеешь радовать",
    "Ты невероятно крутой", "С тобой любая компания — праздник", "Ты очень мудрый",
    "Твоё мнение важно", "Ты заботишься о других", "Ты умеешь признавать ошибки",
    "Ты растёшь и становишься лучше", "Ты достоин восхищения",
    "С тобой я чувствую себя собой", "Ты — лучший!",
]

ЦЕНА_СТАТУСА = 1
ЦЕНА_УЗНАТЬ_АВТОРА = 15
ПОПОЛНЕНИЕ_ВАРИАНТЫ = [1, 10, 50, 100]

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

def отправить_счёт(chat_id, title, description, payload, stars):
    return api("sendInvoice", {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": title, "amount": stars}]
    })

def вернуть_звёзды(user_id, charge_id):
    return api("refundStarPayment", {
        "user_id": user_id,
        "telegram_payment_charge_id": charge_id
    })

def кнопка_добавления(uid):
    return {"inline_keyboard": [
        [{"text": "➕ Добавить в чат (кнопка)", "url": "tg://resolve?domain=" + BOT_USERNAME + "&startgroup=true"}],
        [{"text": "📋 Скопировать @username", "copy_text": {"text": "@" + BOT_USERNAME}}],
        [{"text": "❓ Как добавить вручную", "callback_data": "howto_add"}]
    ]}

def плохой_статус(текст):
    t = текст.lower()
    запрет = ["http://", "https://", "t.me/", "www.", ".com", ".ru", ".org", ".net"]
    for з in запрет:
        if з in t: return True
    if "@" in текст: return True
    return False

def load():
    global чаты, users_reg
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                чаты = {int(k): v for k, v in data.get("чаты", {}).items()}
                users_reg = {int(k): v for k, v in data.get("users_reg", {}).items()}
        except Exception as e:
            print("Ошибка загрузки:", e)
            чаты = {}
            users_reg = {}

def save():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "чаты": {str(k): v for k, v in чаты.items()},
                "users_reg": {str(k): v for k, v in users_reg.items()},
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка сохранения:", e)

def новый_чат():
    return {"игроки": {}, "история": {}, "список_msg_id": None,
            "дуэли": [], "значки": {}}

def получить_чат(cid):
    c = чаты.get(cid)
    if not c:
        c = новый_чат()
        чаты[cid] = c
    if "значки" not in c: c["значки"] = {}
    if "дуэли" not in c: c["дуэли"] = []
    if "история" not in c: c["история"] = {}
    if "игроки" not in c: c["игроки"] = {}
    return c

def получить_юзера(uid):
    u = users_reg.get(uid)
    if not u:
        u = {"имя": None, "очки": 0, "очки_всего": 0, "чаты": [],
             "получено": 0, "отправлено": 0, "угадали": 0,
             "balance": 0, "статус": "", "покупки": []}
        users_reg[uid] = u
    if "balance" not in u: u["balance"] = 0
    if "статус" not in u: u["статус"] = ""
    if "покупки" not in u: u["покупки"] = []
    return u

def звание(очки):
    if очки >= 100: return "Хранитель тайн"
    if очки >= 61:  return "Легенда чата"
    if очки >= 31:  return "Душа компании"
    if очки >= 11:  return "Друг"
    return "Новичок"

def значок_игрока(uid):
    for c in чаты.values():
        з = c.get("значки", {}).get(str(uid))
        if з: return з
    return ""

def имя_с_украшениями(uid, имя):
    знак = значок_игрока(uid)
    if знак: return знак + " " + имя
    return имя

def кнопки_списка(chat_id):
    return kb([
        [("📝 Зарегистрироваться", "reg_me")],
        [("💌 Отправить комплимент", "send_comp")],
        [("👥 Список участников", "refresh")],
        [("🏆 Топ недели", "top")],
        [("🌍 Топ за всё время", "top_all")],
        [("👤 Мой профиль", "profile")],
        [("💎 Магазин", "shop")],
        [("⚔ Дуэль", "duel")],
        [("❓ Помощь", "help")]
    ])

def текст_списка(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "👥 Участники\n\nПока никто не зарегистрирован.\n\n📝 Жми «Зарегистрироваться»!"
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки", 0))
    s = "👥 Участники (" + str(len(sp)) + "):\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (u_id, имя) in enumerate(sp):
        u = users_reg.get(int(u_id), {})
        m = medals[i] if i < 3 else str(i + 1) + "."
        s += m + " " + имя_с_украшениями(u_id, имя) + " — " + str(u.get("очки", 0)) + " очк.\n"
    s += "\n📝 /send_comp — комплимент\n⚔ /duel Имя — дуэль"
    return s

def топ_текст(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "🏆 Топ недели\n\nПока никого."
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки", 0))[:10]
    s = "🏆 Топ недели:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (u_id, имя) in enumerate(sp):
        u = users_reg.get(int(u_id), {})
        m = medals[i] if i < 3 else str(i + 1) + "."
        s += m + " " + имя_с_украшениями(u_id, имя) + " — " + str(u.get("очки", 0)) + " очк. [" + звание(u.get("очки", 0)) + "]\n"
    return s

def топ_всё_время(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "🌍 Топ за всё время\n\nПока никого."
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки_всего", 0))[:10]
    s = "🌍 Топ за всё время:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (u_id, имя) in enumerate(sp):
        u = users_reg.get(int(u_id), {})
        m = medals[i] if i < 3 else str(i + 1) + "."
        s += m + " " + имя_с_украшениями(u_id, имя) + " — " + str(u.get("очки_всего", 0)) + " очк.\n"
    return s

def профиль_текст(uid):
    u = users_reg.get(uid)
    if not u or not u.get("имя"):
        return "❌ Ты не зарегистрирован."
    имя_с_укр = имя_с_украшениями(uid, u["имя"])
    s = "👤 Профиль: " + имя_с_укр + "\n"
    if u.get("статус"):
        s += "🎭 " + u["статус"] + "\n"
    s += "\n"
    s += "🏆 Очки (неделя): " + str(u.get("очки", 0)) + "\n"
    s += "🌍 Очки (всего): " + str(u.get("очки_всего", 0)) + "\n"
    s += "🎖 Звание: " + звание(u.get("очки_всего", 0)) + "\n"
    s += "💰 Баланс: " + str(u.get("balance", 0)) + "⭐\n\n"
    s += "💌 Отправлено: " + str(u.get("отправлено", 0)) + "\n"
    s += "📥 Получено: " + str(u.get("получено", 0)) + "\n"
    s += "🎯 Угадали тебя: " + str(u.get("угадали", 0)) + " раз"
    return s

def обновить_список(chat_id):
    c = получить_чат(chat_id)
    old = c.get("список_msg_id")
    if old:
        try: api("deleteMessage", {"chat_id": chat_id, "message_id": old})
        except: pass
    r = send(chat_id, текст_списка(chat_id), кнопки_списка(chat_id))
    msg_id = r.get("result", {}).get("message_id")
    if msg_id:
        c["список_msg_id"] = msg_id
        save()
        try:
            api("pinChatMessage", {"chat_id": chat_id, "message_id": msg_id, "disable_notification": True})
        except: pass

def кнопки_магазина(uid):
    return kb([
        [("💳 Пополнить баланс", "topup_menu")],
        [("🎭 Поставить статус — " + str(ЦЕНА_СТАТУСА) + "⭐", "buy_status")],
        [("🔓 Узнать автора — " + str(ЦЕНА_УЗНАТЬ_АВТОРА) + "⭐", "buy_reveal")],
        [("⬅ Назад", "shop_back")]
    ])

def кнопки_пополнения():
    rows = []
    for сумма in ПОПОЛНЕНИЕ_ВАРИАНТЫ:
        rows.append([{"text": "+" + str(сумма) + "⭐", "callback_data": "topup_" + str(сумма)}])
    rows.append([{"text": "⬅ Назад", "callback_data": "shop"}])
    return {"inline_keyboard": rows}

def текст_магазина(uid):
    u = получить_юзера(uid)
    return ("💎 МАГАЗИН\n\n"
            "💰 Твой баланс: " + str(u.get("balance", 0)) + "⭐\n\n"
            "🎭 Статус в профиле — " + str(ЦЕНА_СТАТУСА) + "⭐\n"
            "Строка под именем (до 20 символов).\n\n"
            "🔓 Узнать автора — " + str(ЦЕНА_УЗНАТЬ_АВТОРА) + "⭐\n"
            "Мгновенно раскроет, кто отправил комплимент.\n\n"
            "💳 Пополни баланс звёздами Telegram.")

def текст_пополнения(uid):
    u = получить_юзера(uid)
    return "💳 ПОПОЛНЕНИЕ\n\n💰 Сейчас: " + str(u.get("balance", 0)) + "⭐\n\nВыбери сумму:"

def кнопки_выбора_жертвы(chat_id, uid):
    c = получить_чат(chat_id)
    rows = []
    for u_id, имя in c["игроки"].items():
        if int(u_id) == uid: continue
        rows.append([{"text": имя, "callback_data": "pick_" + str(chat_id) + "_" + u_id}])
    if not rows:
        return None
    return {"inline_keyboard": rows}

def отправить_комплимент(chat_id, от_uid, кому_uid, текст):
    c = получить_чат(chat_id)
    u_от = получить_юзера(от_uid)
    u_кому = получить_юзера(кому_uid)
    u_от["очки"] = u_от.get("очки", 0) + 1
    u_от["очки_всего"] = u_от.get("очки_всего", 0) + 1
    u_от["отправлено"] = u_от.get("отправлено", 0) + 1
    u_кому["получено"] = u_кому.get("получено", 0) + 1
    c["история"].setdefault(str(кому_uid), [])
    c["история"][str(кому_uid)].append({"от": от_uid, "текст": текст, "угадано": False})
    учесть_комплимент_в_дуэли(chat_id, кому_uid)
    save()
    send(chat_id, "💌 " + u_кому["имя"] + ", тебе анонимный комплимент:\n\n«" + текст + "»")
    send(кому_uid, "💌 Тебе анонимный комплимент:\n\n«" + текст + "»",
         kb([[("🎯 Угадать автора", "gues_" + str(chat_id) + "_" + str(кому_uid))]]))
    send(от_uid, "✅ Комплимент отправлен! +1 очко")

def создать_дуэль(chat_id, uid1, uid2):
    c = получить_чат(chat_id)
    d = {"игрок1": str(uid1), "игрок2": str(uid2), "очки1": 0, "очки2": 0,
         "старт": time.time(), "завершена": False}
    c["дуэли"].append(d)
    idx = len(c["дуэли"]) - 1
    save()
    threading.Thread(target=таймер_дуэли, args=(chat_id, idx), daemon=True).start()
    return d

def таймер_дуэли(chat_id, idx):
    time.sleep(24 * 60 * 60)
    try:
        c = получить_чат(chat_id)
        if idx >= len(c["дуэли"]): return
        d = c["дуэли"][idx]
        if d.get("завершена"): return
        d["завершена"] = True
        имя1 = users_reg.get(int(d["игрок1"]), {}).get("имя", "???")
        имя2 = users_reg.get(int(d["игрок2"]), {}).get("имя", "???")
        if d["очки1"] > d["очки2"]: поб = d["игрок1"]
        elif d["очки2"] > d["очки1"]: поб = d["игрок2"]
        else: поб = None
        if поб:
            u = получить_юзера(int(поб))
            u["очки"] = u.get("очки", 0) + 20
            u["очки_всего"] = u.get("очки_всего", 0) + 20
            send(chat_id, "⚔ ДУЭЛЬ ЗАВЕРШЕНА!\n\n" + имя1 + " vs " + имя2 + "\n📊 " + str(d["очки1"]) + " : " + str(d["очки2"]) + "\n\n🏆 Победитель: " + u["имя"] + " — +20 очков!")
        else:
            send(chat_id, "⚔ ДУЭЛЬ ЗАВЕРШЕНА!\n\n" + имя1 + " vs " + имя2 + "\n📊 " + str(d["очки1"]) + " : " + str(d["очки2"]) + "\n\n🤝 Ничья!")
        save()
    except Exception as e:
        print("Ошибка дуэли:", e)

def учесть_комплимент_в_дуэли(chat_id, кому_uid):
    c = получить_чат(chat_id)
    for d in c["дуэли"]:
        if d.get("завершена"): continue
        if str(кому_uid) == d["игрок1"]: d["очки1"] += 1
        elif str(кому_uid) == d["игрок2"]: d["очки2"] += 1
    save()

admin_session = {}

def админ_меню(uid):
    счёт = len([u for u in users_reg.values() if u.get("имя")])
    покупок = sum(len(u.get("покупки", [])) for u in users_reg.values())
    send(uid,
         "👑 АДМИН-МЕНЮ\n\n👥 Зарегистрировано: " + str(счёт) + "\n💬 Чатов: " + str(len(чаты)) + "\n💸 Покупок: " + str(покупок) + "\n\nДействия:",
         {"inline_keyboard": [
             [{"text": "📊 Все пользователи", "callback_data": "admin_users"}],
             [{"text": "💬 Все чаты", "callback_data": "admin_chats"}],
             [{"text": "🎖 Выдать значок", "callback_data": "admin_icon"}],
             [{"text": "💸 Вернуть деньги", "callback_data": "admin_refund"}],
             [{"text": "❌ Закрыть", "callback_data": "admin_close"}]
         ]})

def меню_значков(target_uid):
    return {"inline_keyboard": [
        [{"text": "👑 Главный админ", "callback_data": "seticon_👑_" + target_uid}],
        [{"text": "🛡 Помощник", "callback_data": "seticon_🛡_" + target_uid}],
        [{"text": "⭐ Проверенный", "callback_data": "seticon_⭐_" + target_uid}],
        [{"text": "🧪 Тестировщик", "callback_data": "seticon_🧪_" + target_uid}],
        [{"text": "❌ Убрать значок", "callback_data": "seticon_❌_" + target_uid}],
        [{"text": "↩ Назад", "callback_data": "admin_back"}]
    ]}

def обработка_лички(uid, text, payload=None):
    low = text.strip().lower()
    u = получить_юзера(uid)
    if low == "/reset":
        u["имя"] = None
        save()
        send(uid, "✅ Сброшено. Напиши /start заново.")
        return
    if low == "/cancel":
        u["_wait_status"] = False
        u["_wait_own"] = None
        u["_wait_admin"] = False
        save()
        send(uid, "❌ Отменено.")
        return
    if u.get("_wait_status"):
        if low.startswith("/"):
            send(uid, "❌ Отмена. Напиши статус текстом, или /cancel.")
            return
        статус = text.strip()[:20]
        if not статус:
            send(uid, "❌ Пусто. Напиши что-нибудь.")
            return
        if плохой_статус(статус):
            send(uid, "❌ В статусе нельзя ссылки и @username. Попробуй снова:")
            return
        u["статус"] = статус
        u["_wait_status"] = False
        save()
        send(uid, "✅ Статус установлен: 🎭 " + статус)
        for cid_s in u.get("чаты", []):
            try: обновить_список(int(cid_s))
            except: pass
        return
    if u.get("_wait_own"):
        if low.startswith("/"):
            send(uid, "❌ Отмена. Напиши комплимент текстом, или /cancel.")
            return
        data = u["_wait_own"]
        chat_id = data["chat"]
        кому_uid = data["to"]
        текст = text.strip()[:200]
        if текст:
            отправить_комплимент(chat_id, uid, кому_uid, текст)
        u["_wait_own"] = None
        save()
        return
    if u.get("имя") is None:
        if low == "/start" or payload:
            send(uid, "👋 Привет! Я — Тайный Друг 🎭\n\nПомогаю отправлять анонимные комплименты друзьям.\n\n📝 Как тебя зовут? Напиши своё имя:")
            return
        if not text.startswith("/"):
            имя = text.strip()[:20]
            u["имя"] = имя
            save()
            счёт = len([x for x in users_reg.values() if x.get("имя")])
            send(uid,
                 "✅ Отлично, " + имя + "!\n\n"
                 "🎭 Тайный Друг — анонимные комплименты для чата.\n\n"
                 "🎯 КАК ИГРАТЬ\n"
                 "1️⃣ Добавь меня в чат\n"
                 "2️⃣ Друзья жмут «Зарегистрироваться»\n"
                 "3️⃣ Отправляй комплименты (🎲 или ✍️)\n"
                 "4️⃣ Угадывай авторов по кнопке\n"
                 "5️⃣ Соревнуйся в топах\n\n"
                 "💎 ОЧКИ\n"
                 "+1 — за комплимент\n"
                 "+2 — угадал автора\n"
                 "+3 — тебя НЕ угадали\n"
                 "+20 — победа в дуэли\n\n"
                 "👥 Всего в боте: " + str(счёт) + " чел.\n\n"
                 "👇 Жми:",
                 кнопка_добавления(uid))
            return
    if low == "/admin":
        send(uid, "🔐 Введи пароль админа:")
        u["_wait_admin"] = True
        save()
        return
    if u.get("_wait_admin"):
        if text.strip() == ADMIN_PASSWORD:
            u["_wait_admin"] = False
            save()
            admin_session[uid] = True
            админ_меню(uid)
        else:
            u["_wait_admin"] = False
            save()
            send(uid, "❌ Неверный пароль.")
        return
    if low == "/shop":
        send(uid, текст_магазина(uid), кнопки_магазина(uid))
        return
    if low == "/chatid":
        send(uid, "🆔 Мой chat_id: " + str(uid))
        return
    if low == "/start" and not payload:
        счёт = len([x for x in users_reg.values() if x.get("имя")])
        send(uid,
             "👋 Привет, " + u["имя"] + "!\n\n"
             "Я — Тайный Друг 🎭\n\n"
             "📋 Как играть:\n"
             "1️⃣ Добавь меня в чат\n"
             "2️⃣ Кто-то пишет /start в чате\n"
             "3️⃣ Жми «Зарегистрироваться»\n"
             "4️⃣ Отправляй комплименты\n\n"
             "💰 Баланс: " + str(u.get("balance", 0)) + "⭐\n"
             "👥 Всего в боте: " + str(счёт) + " чел.\n\n"
             "👇 Добавь меня в чат:",
             кнопка_добавления(uid))
        return
    if low == "/help":
        send(uid, "📖 Команды:\n\nВ чате: кнопки в меню\n\nВ личке:\n• /shop — магазин\n• /admin — админка\n• /chatid — ID\n• /reset — сброс профиля\n• /cancel — отменить ввод")
        return
    send(uid, "Не понял. /start")

def обработка_группы(chat_id, uid, text):
    print("[ГРУППА] chat=" + str(chat_id) + " uid=" + str(uid) + " text=" + repr(text))
    low = text.strip().lower()
    c = получить_чат(chat_id)
    if low == "/start":
        send(chat_id, "💌 Тайный Друг\n\n🎯 Анонимные комплименты друзьям.\n\n👇 Жми:", кнопки_списка(chat_id))
        return
    if low == "/send_comp":
        send(chat_id, "💌 Жми кнопку:", кнопки_списка(chat_id))
        return
    if low == "/chatid":
        send(chat_id, "🆔 chat_id этой группы: " + str(chat_id))
        return
    if low.startswith("/duel"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat_id, "❌ Напиши: /duel Имя"); return
        имя = parts[1].strip().lower()
        target = None
        for k, v in c["игроки"].items():
            if v.lower() == имя: target = k; break
        if not target:
            send(chat_id, "❌ «" + имя + "» не найден."); return
        if target == str(uid):
            send(chat_id, "😄 Себе вызов не бросить!"); return
        if str(uid) not in c["игроки"]:
            send(chat_id, "❌ Сначала зарегистрируйся!"); return
        создать_дуэль(chat_id, int(uid), int(target))
        имя1 = c["игроки"][str(uid)]
        имя2 = c["игроки"][target]
        send(chat_id, "⚔ ДУЭЛЬ!\n\n" + имя1 + " vs " + имя2 + "\n\n🏆 Победитель: +20 очков!")
        return
    if low == "/players":
        send(chat_id, текст_списка(chat_id), кнопки_списка(chat_id))
        return

def запустить_веб_сервер():
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

def обработать_оплату(uid, payload, chat_id=None):
    u = получить_юзера(uid)
    if payload.startswith("topup_"):
        try: сумма = int(payload.replace("topup_", ""))
        except: сумма = 0
        if сумма > 0:
            u["balance"] = u.get("balance", 0) + сумма
            save()
            send(uid, "✅ Баланс пополнен на " + str(сумма) + "⭐\n\n💰 Текущий: " + str(u["balance"]) + "⭐")
        return
    if payload == "buy_status":
        if u.get("balance", 0) < ЦЕНА_СТАТУСА:
            send(uid, "❌ Не хватает звёзд."); return
        u["balance"] -= ЦЕНА_СТАТУСА
        u["_wait_status"] = True
        save()
        send(uid, "🎭 Напиши свой статус (до 20 символов):")
        return
    if payload == "buy_reveal":
        if u.get("balance", 0) < ЦЕНА_УЗНАТЬ_АВТОРА:
            send(uid, "❌ Не хватает звёзд."); return
        u["balance"] -= ЦЕНА_УЗНАТЬ_АВТОРА
        save()
        найдено = False
        for cid_s in u.get("чаты", []):
            cid = int(cid_s)
            c = получить_чат(cid)
            история = c.get("история", {}).get(str(uid), [])
            for h in reversed(история):
                if not h.get("угадано"):
                    авт = users_reg.get(h["от"], {}).get("имя", "???")
                    send(uid, "🔓 Автор: " + авт + "\n\n💌 «" + h["текст"] + "»")
                    h["угадано"] = True
                    save()
                    найдено = True
                    break
            if найдено: break
        if not найдено:
            u["balance"] += ЦЕНА_УЗНАТЬ_АВТОРА
            save()
            send(uid, "❌ Нет неразгаданных. Возврат.")

load()
print("Бот запущен: @" + BOT_USERNAME)
threading.Thread(target=запустить_веб_сервер, daemon=True).start()

while True:
    try:
        r = requests.get(API + "/getUpdates",
                         params={"offset": offset, "timeout": 20,
                                 "allowed_updates": '["message","callback_query","my_chat_member","pre_checkout_query"]'},
                         timeout=25)
        data = r.json()
        if not data.get("ok"):
            print("Err:", data); time.sleep(2); continue
        for upd in data["result"]:
            offset = upd["update_id"] + 1
            pcq = upd.get("pre_checkout_query")
            if pcq:
                api("answerPreCheckoutQuery", {"pre_checkout_query_id": pcq["id"], "ok": True})
                continue
            mcm = upd.get("my_chat_member")
            if mcm:
                chat = mcm["chat"]
                new_status = mcm["new_chat_member"]["status"]
                chat_id = chat["id"]
                if chat_id < 0 and new_status in ("member", "administrator"):
                    получить_чат(chat_id)
                    save()
                    print("[НОВЫЙ ЧАТ] " + str(chat_id))
                    send(chat_id, "👋 Привет, ребята!\n\nЯ — Тайный Друг 🎭\n🎯 Цель: стать «Душой компании».\n\n👇 Жми Старт:",
                         kb([[("🚀 Старт", "begin")]]))
                continue
            cb = upd.get("callback_query")
            if cb:
                uid = cb["from"]["id"]
                chat_id = cb["message"]["chat"]["id"]
                act = cb["data"]
                u = получить_юзера(uid)
                c = получить_чат(chat_id)
                if act == "begin":
                    answer_cb(cb["id"], "🚀")
                    send(chat_id, "💌 Меню:", кнопки_списка(chat_id))
                elif act == "howto_add":
                    answer_cb(cb["id"])
                    send(uid, "📖 КАК ДОБАВИТЬ БОТА В ЧАТ\n\nСпособ 1: жми «➕ Добавить в чат (кнопка)»\n\nСпособ 2 (вручную):\n• Открой группу → название → Управление → Участники → Добавить\n• Введи: @" + BOT_USERNAME + "\n\nСпособ 3: жми «📋 Скопировать @username» и вставь в поиск Telegram")
                elif act == "reg_me":
                    if not u.get("имя"):
                        answer_cb(cb["id"], "📝 Сначала /start в личке.", alert=True)
                    else:
                        c["игроки"][str(uid)] = u["имя"]
                        if chat_id not in u["чаты"]:
                            u["чаты"].append(chat_id)
                        save()
                        answer_cb(cb["id"], "✅ Зарегистрирован!")
                        send(chat_id, "✅ " + u["имя"] + " зарегистрирован!")
                        обновить_список(chat_id)
                elif act == "send_comp":
                    if not u.get("имя"):
                        answer_cb(cb["id"], "📝 Сначала /start в личке.", alert=True)
                    elif str(uid) not in c["игроки"]:
                        answer_cb(cb["id"], "❌ Сначала зарегистрируйся!", alert=True)
                    else:
                        клав = кнопки_выбора_жертвы(chat_id, uid)
                        if клав:
                            answer_cb(cb["id"], "💌 Лови в личке!")
                            send(uid, "💌 Кому отправить комплимент?", клав)
                        else:
                            answer_cb(cb["id"], "Нет других участников", alert=True)
                elif act.startswith("pick_"):
                    parts = act.split("_")
                    real_chat = int(parts[1])
                    target_uid = int(parts[2])
                    answer_cb(cb["id"])
                    имя_цели = чаты.get(real_chat, {}).get("игроки", {}).get(str(target_uid), "???")
                    send(uid, "Кому: " + имя_цели + "\n\nКак отправить?",
                         kb([
                             [("🎲 Случайный", "rand_" + str(real_chat) + "_" + str(target_uid))],
                             [("✍️ Свой текст", "own_" + str(real_chat) + "_" + str(target_uid))]
                         ]))
                elif act.startswith("rand_"):
                    parts = act.split("_")
                    real_chat = int(parts[1])
                    target_uid = int(parts[2])
                    answer_cb(cb["id"], "🎲")
                    текст = random.choice(КОМПЛИМЕНТЫ)
                    отправить_комплимент(real_chat, uid, target_uid, текст)
                elif act.startswith("own_"):
                    parts = act.split("_")
                    real_chat = int(parts[1])
                    target_uid = int(parts[2])
                    answer_cb(cb["id"])
                    u["_wait_own"] = {"chat": real_chat, "to": target_uid}
                    save()
                    имя_цели = чаты.get(real_chat, {}).get("игроки", {}).get(str(target_uid), "???")
                    send(uid, "✍️ Напиши комплимент для " + имя_цели + ":")
                elif act.startswith("gues_"):
                    parts = act.split("_")
                    real_chat = int(parts[1])
                    target_uid = int(parts[2])
                    answer_cb(cb["id"])
                    cg = получить_чат(real_chat)
                    rows = []
                    for u_id, имя in cg["игроки"].items():
                        if int(u_id) == target_uid: continue
                        rows.append([{"text": имя, "callback_data": "pu_" + str(real_chat) + "_" + str(target_uid) + "_" + u_id}])
                    if not rows:
                        send(uid, "Никого нет.")
                    else:
                        send(uid, "🎯 Кто отправил последний комплимент?", {"inline_keyboard": rows})
                elif act.startswith("pu_"):
                    parts = act.split("_")
                    real_chat = int(parts[1])
                    target_uid = int(parts[2])
                    автор_uid = int(parts[3])
                    answer_cb(cb["id"])
                    cg = получить_чат(real_chat)
                    история = cg.get("история", {}).get(str(target_uid), [])
                    last = None
                    for h in reversed(история):
                        if not h.get("угадано"): last = h; break
                    if not last:
                        send(uid, "❌ Комплимент уже разгадан.")
                        continue
                    реальный = last["от"]
                    имя_автора = users_reg.get(реальный, {}).get("имя", "???")
                    if автор_uid == реальный:
                        last["угадано"] = True
                        for tu_id in (target_uid, реальный):
                            tu = users_reg.get(tu_id)
                            tu["очки"] = tu.get("очки", 0) + 2
                            tu["очки_всего"] = tu.get("очки_всего", 0) + 2
                        users_reg[реальный]["угадали"] = users_reg[реальный].get("угадали", 0) + 1
                        save()
                        send(uid, "🎉 Точно! Это был(а) " + имя_автора + "! +2 очка")
                        send(реальный, "👀 Тебя раскрыли! +2 очка")
                    else:
                        last["угадано"] = True
                        au = users_reg.get(реальный)
                        au["очки"] = au.get("очки", 0) + 3
                        au["очки_всего"] = au.get("очки_всего", 0) + 3
                        save()
                        send(uid, "❌ Не угадал. Автор остался в тайне. +3 очка автору.")
                        send(реальный, "😎 Ты остался загадкой! +3 очка")
                elif act == "shop":
                    answer_cb(cb["id"])
                    send(uid, текст_магазина(uid), кнопки_магазина(uid))
                elif act == "shop_back":
                    answer_cb(cb["id"])
                    send(chat_id, "💌 Меню:", кнопки_списка(chat_id))
                elif act == "topup_menu":
                    answer_cb(cb["id"])
                    send(uid, текст_пополнения(uid), кнопки_пополнения())
                elif act.startswith("topup_"):
                    answer_cb(cb["id"])
                    try: сумма = int(act.replace("topup_", ""))
                    except: сумма = 10
                    отправить_счёт(uid, "💰 Пополнение", "Зачисление " + str(сумма) + " звёзд", "topup_" + str(сумма), сумма)
                elif act == "buy_status":
                    answer_cb(cb["id"])
                    if u.get("balance", 0) < ЦЕНА_СТАТУСА:
                        send(uid, "❌ Не хватает звёзд (" + str(u.get("balance", 0)) + "⭐). /shop")
                    else:
                        u["balance"] -= ЦЕНА_СТАТУСА
                        u["_wait_status"] = True
                        save()
                        send(uid, "🎭 Напиши свой статус (до 20 символов):")
                elif act == "buy_reveal":
                    answer_cb(cb["id"])
                    if u.get("balance", 0) < ЦЕНА_УЗНАТЬ_АВТОРА:
                        send(uid, "❌ Не хватает звёзд (" + str(u.get("balance", 0)) + "⭐). /shop")
                    else:
                        u["balance"] -= ЦЕНА_УЗНАТЬ_АВТОРА
                        save()
                        найдено = False
                        for cid_s in u.get("чаты", []):
                            cid = int(cid_s)
                            cg = получить_чат(cid)
                            история = cg.get("история", {}).get(str(uid), [])
                            for h in reversed(история):
                                if not h.get("угадано"):
                                    авт = users_reg.get(h["от"], {}).get("имя", "???")
                                    send(uid, "🔓 Автор: " + авт + "\n\n💌 «" + h["текст"] + "»")
                                    h["угадано"] = True
                                    save()
                                    найдено = True
                                    break
                            if найдено: break
                        if not найдено:
                            u["balance"] += ЦЕНА_УЗНАТЬ_АВТОРА
                            save()
                            send(uid, "❌ Нет неразгаданных. Возврат.")
                elif act == "status_change":
                    answer_cb(cb["id"])
                    if not u.get("статус"):
                        send(uid, "❌ Статуса нет. Купи в /shop за " + str(ЦЕНА_СТАТУСА) + "⭐")
                    else:
                        u["_wait_status"] = True
                        save()
                        send(uid, "🎭 Напиши новый статус (до 20 символов):")
                elif act == "refresh":
                    answer_cb(cb["id"], "🔄")
                    send(chat_id, "📋 Список:\n\n" + текст_списка(chat_id), кнопки_списка(chat_id))
                elif act == "top":
                    answer_cb(cb["id"]); send(chat_id, топ_текст(chat_id))
                elif act == "top_all":
                    answer_cb(cb["id"]); send(chat_id, топ_всё_время(chat_id))
                elif act == "profile":
                    answer_cb(cb["id"])
                    send(chat_id, профиль_текст(uid),
                         kb([[("🎭 Сменить статус", "status_change")]]))
                elif act == "duel":
                    answer_cb(cb["id"]); send(chat_id, "⚔ /duel Имя")
                elif act == "help":
                    answer_cb(cb["id"])
                    send(chat_id, "📖 Как играть:\n1. Зарегистрируйся\n2. Отправляй комплименты\n3. Угадывай авторов по кнопке\n4. Соревнуйся в топах\n\n💎 Магазин — /shop")
                elif act == "admin_users":
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    люди = [(k, uu) for k, uu in users_reg.items() if uu.get("имя")]
                    if not люди:
                        send(uid, "Никто не зарегистрирован."); continue
                    s = "👥 Всего: " + str(len(люди)) + "\n\n"
                    for i, (uu_id, uu) in enumerate(люди[:30], 1):
                        s += str(i) + ". " + uu["имя"]
                        if uu.get("balance", 0) > 0:
                            s += " 💰" + str(uu["balance"]) + "⭐"
                        s += "\n"
                    send(uid, s)
                elif act == "admin_chats":
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    if not чаты:
                        send(uid, "Бот пока не в чатах."); continue
                    s = "💬 Чатов: " + str(len(чаты)) + "\n\n"
                    for cid, cc in list(чаты.items())[:20]:
                        s += "• " + str(cid) + " — " + str(len(cc["игроки"])) + " игроков\n"
                    send(uid, s)
                elif act == "admin_icon":
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    люди = [(k, uu) for k, uu in users_reg.items() if uu.get("имя")]
                    if not люди:
                        send(uid, "Никто не зарегистрирован."); continue
                    rows = []
                    for uu_id, uu in люди[:20]:
                        rows.append([{"text": uu["имя"], "callback_data": "pickuser_" + str(uu_id)}])
                    send(uid, "Кому значок?", {"inline_keyboard": rows})
                elif act.startswith("pickuser_"):
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    target_uid = act.replace("pickuser_", "")
                    имя = users_reg.get(int(target_uid), {}).get("имя", "???")
                    send(uid, "Значок для " + имя + ":", меню_значков(target_uid))
                elif act.startswith("seticon_"):
                    parts = act.split("_")
                    значок = parts[1]; target_uid = parts[2]
                    if not admin_session.get(uid): continue
                    found = False
                    for cid, cc in чаты.items():
                        if target_uid in cc["игроки"]:
                            if значок == "❌":
                                cc["значки"].pop(target_uid, None)
                                send(uid, "✅ Убран.")
                            else:
                                cc["значки"][target_uid] = значок
                                send(uid, "✅ " + значок + " выдан " + cc["игроки"][target_uid] + "!")
                            found = True
                            обновить_список(cid)
                            break
                    if not found:
                        send(uid, "❌ Игрок не в чате.")
                    save()
                    админ_меню(uid)
                elif act == "admin_refund":
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    всего = 0
                    успешно = 0
                    провал = 0
                    for uu_id, uu in users_reg.items():
                        for покупка in list(uu.get("покупки", [])):
                            charge_id = покупка.get("charge_id", "")
                            if not charge_id: continue
                            всего += 1
                            r = вернуть_звёзды(uu_id, charge_id)
                            if r.get("ok"):
                                успешно += 1
                                uu["покупки"].remove(покупка)
                            else:
                                провал += 1
                    save()
                    send(uid, "💸 Возврат завершён\n\nВсего: " + str(всего) + "\n✅ Успешно: " + str(успешно) + "\n❌ Ошибок: " + str(провал))
                elif act == "admin_back":
                    answer_cb(cb["id"]); админ_меню(uid)
                elif act == "admin_close":
                    answer_cb(cb["id"], "Закрыто"); admin_session.pop(uid, None)
                else:
                    answer_cb(cb["id"])
                continue
            msg = upd.get("message")
            if not msg: continue
            chat_id = msg["chat"]["id"]
            uid = msg["from"]["id"]
            text = msg.get("text") or ""
            if msg.get("successful_payment"):
                sp = msg["successful_payment"]
                payload = sp.get("invoice_payload", "")
                charge_id = sp.get("telegram_payment_charge_id", "")
                u = получить_юзера(uid)
                u.setdefault("покупки", []).append({"charge_id": charge_id, "payload": payload})
                save()
                print("[ОПЛАТА] uid=" + str(uid) + " payload=" + payload + " charge=" + charge_id)
                обработать_оплату(uid, payload, chat_id)
                continue
            payload = None
            if text.startswith("/start "):
                payload = text.split(maxsplit=1)[1]
                text = "/start"
            if chat_id > 0:
                обработка_лички(uid, text, payload)
            else:
                if text:
                    обработка_группы(chat_id, uid, text)
    except Exception as e:
        print("Ошибка:", e); time.sleep(3)
