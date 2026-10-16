import requests
import time
import json
import os
import random
import threading
import http.server
import socketserver

TOKEN = "8918941174:AAE6VYeW4cPTsGInySM0W_4J1Dq6XmpPO4M"
API = "https://api.telegram.org/bot" + TOKEN
SAVE_FILE = "secret_friend.json"
offset = 0

ADMIN_PASSWORD = "12345"
BOT_USERNAME = "Tajnij_dryg_bot"

users_reg = {}
чаты = {}

КОМПЛИМЕНТЫ = [
    "Ты сегодня просто огонь", "С тобой всегда весело", "Ты очень умный, не забывай об этом",
    "Твоя улыбка делает день лучше", "Ты классный друг, спасибо что ты есть",
    "Твоя энергия заражает всех вокруг", "Ты умеешь поддержать в нужный момент",
    "С тобой не страшно ничего", "Ты очень талантливый", "Твоё чувство юмора — топ",
    "Ты делаешь этот мир лучше", "С тобой время летит незаметно", "Ты настоящий друг",
    "Твоя доброта бесценна", "Ты вдохновляешь меня", "С тобой любое дело по плечу",
    "Ты очень отзывчивый", "Твоя поддержка много значит", "Ты классно выглядишь сегодня",
    "Ты всегда найдёшь нужные слова", "С тобой интересно болтать", "Ты очень честный",
    "Твоя искренность подкупает", "Ты заслуживаешь всего лучшего", "Ты очень стильный",
    "С тобой весело даже в дождь", "Ты настоящий лидер", "Твоя настойчивость впечатляет",
    "Ты умеешь мечтать", "Ты очень внимательный", "С тобой уютно молчать",
    "Ты умеешь слушать", "Твои идеи — огонь", "Ты творческая личность",
    "У тебя отличный вкус", "Ты очень терпеливый", "С тобой хочется дружить",
    "Ты надёжный, как скала", "Твоя улыбка заразительна", "Ты умеешь радовать",
    "Ты невероятно крутой", "С тобой любая компания — праздник", "Ты очень мудрый",
    "Твоё мнение важно", "Ты заботишься о других", "Ты умеешь признавать ошибки",
    "Ты растёшь и становишься лучше", "Ты достоин восхищения",
    "С тобой я чувствую себя собой", "Ты — лучший!",
]

ЦЕНА_ЦВЕТ_ИМЯ = 1
ЦЕНА_УЗНАТЬ_АВТОРА = 15
ПОПОЛНЕНИЕ_ВАРИАНТЫ = [10, 50, 100]

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

def отправить_счёт(chat_id, title, description, payload, stars):
    return api("sendInvoice", {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "currency": "XTR",
        "prices": [{"label": title, "amount": stars}]
    })

def кнопка_добавления():
    return {"inline_keyboard": [
        [{"text": "➕ Добавить в чат (кнопка)", "url": "tg://resolve?domain=" + BOT_USERNAME + "&startgroup=true"}],
        [{"text": "📋 Скопировать @username", "copy_text": {"text": "@" + BOT_USERNAME}}],
        [{"text": "❓ Как добавить вручную", "callback_data": "howto_add"}]
    ]}

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

def новый_чат():
    return {"игроки": {}, "история": {}, "список_msg_id": None,
            "дуэли": [], "значки": {}}

def получить_чат(cid):
    c = чаты.get(cid)
    if not c:
        c = новый_чат()
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
             "цветное_имя": False, "balance": 0}
        users_reg[uid] = u
    if "цветное_имя" not in u: u["цветное_имя"] = False
    if "balance" not in u: u["balance"] = 0
    return u

def звание(очки):
    if очки >= 100: return "Хранитель тайн"
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
    u = users_reg.get(uid, {})
    знак = значок_игрока(uid)
    префикс = ""
    if знак: префикс += знак + " "
    if u.get("цветное_имя"): префикс += "🌈 "
    return префикс + имя

def кнопки_списка(chat_id):
    return kb([
        [("📝 Зарегистрироваться", "reg_me")],
        [("💌 Отправить комплимент", "send_comp")],
        [("👥 Список участников", "refresh")],
        [("🏆 Топ недели", "top")],
        [("🌍 Топ за всё время", "top_all")],
        [("👤 Мой профиль", "profile")],
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

def топ_всё_время(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "🌍 Топ за всё время\n\nПока никого."
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки_всего", 0))[:10]
    s = "🌍 Топ за всё время:\n\n"
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
    s = ("👤 Профиль: " + имя_с_укр + "\n\n"
         "🏆 Очки (неделя): " + str(u.get("очки", 0)) + "\n"
         "🌍 Очки (всего): " + str(u.get("очки_всего", 0)) + "\n"
         "🎖 Звание: " + звание(u.get("очки_всего", 0)) + "\n"
         "💰 Баланс: " + str(u.get("balance", 0)) + "⭐\n\n"
         "💌 Отправлено: " + str(u.get("отправлено", 0)) + "\n"
         "📥 Получено: " + str(u.get("получено", 0)) + "\n"
         "🎯 Угадали тебя: " + str(u.get("угадали", 0)) + " раз\n\n")
    if u.get("цветное_имя"):
        s += "🌈 Цветное имя: активно\n"
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
        [("🌈 Цветное имя — " + str(ЦЕНА_ЦВЕТ_ИМЯ) + "⭐", "buy_color")],
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
            "💰 Твой баланс: " + str(u.get("balance", 0)) + "⭐\n\n"
            "🌈 Цветное имя — " + str(ЦЕНА_ЦВЕТ_ИМЯ) + "⭐\n"
            "🔓 Узнать автора — " + str(ЦЕНА_УЗНАТЬ_АВТОРА) + "⭐\n\n"
            "💳 Пополни баланс звёздами Telegram.")

def текст_пополнения(uid):
    u = получить_юзера(uid)
    return "💳 ПОПОЛНЕНИЕ\n\n💰 Сейчас: " + str(u.get("balance", 0)) + "⭐\n\nВыбери сумму:"

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
    send(chat_id, "💌 " + u_кому["имя"] + ", тебе анонимный комплимент:\n\n«" + текст + "»")
    send(кому_uid, "💌 Тебе анонимный комплимент:\n\n«" + текст + "»\n\nХочешь угадать? /guess")
    send(от_uid, "✅ Комплимент отправлен! +1 очко")

def создать_дуэль(chat_id, uid1, uid2):
    c = получить_чат(chat_id)
    d = {"игрок1": str(uid1), "игрок2": str(uid2), "очки1": 0, "очки2": 0,
         "старт": time.time(), "завершена": False}
    c["дуэли"].append(d)
    idx = len(c["дуэли"]) - 1
    save()
    threading.Thread(target=таймер_дуэли, args=(chat_id, idx), daemon=True).start()
    return d

def таймер_дуэли(chat_id, idx):
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
    счёт = len([u for u in users_reg.values() if u.get("имя")])
    send(uid,
         "👑 АДМИН-МЕНЮ\n\n👥 Зарегистрировано: " + str(счёт) + "\n💬 Чатов: " + str(len(чаты)) + "\n\nДействия:",
         {"inline_keyboard": [
             [{"text": "📊 Все пользователи", "callback_data": "admin_users"}],
             [{"text": "💬 Все чаты", "callback_data": "admin_chats"}],
             [{"text": "🎖 Выдать значок", "callback_data": "admin_icon"}],
             [{"text": "❌ Закрыть", "callback_data": "admin_close"}]
         ]})

def меню_значков(target_uid):
    return {"inline_keyboard": [
        [{"text": "👑 Главный админ", "callback_data": "seticon_👑_" + target_uid}],
        [{"text": "🛡 Помощник", "callback_data": "seticon_🛡_" + target_uid}],
        [{"text": "⭐ Проверенный", "callback_data": "seticon_⭐_" + target_uid}],
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
    if u.get("имя") is None:
        if low == "/start" or payload:
            send(uid, "👋 Привет! Я — Тайный Друг 🎭\n\nПомогаю отправлять анонимные комплименты друзьям.\n\n📝 Как тебя зовут? Напиши своё имя:")
            return
        if not text.startswith("/"):
            имя = text.strip()[:20]
            u["имя"] = имя
            save()
            счёт = len([x for x in users_reg.values() if x.get("имя")])
            send(uid,
                 "✅ Отлично, " + имя + "!\n\n🎯 Что дальше:\n1️⃣ Добавь меня в чат\n2️⃣ Кто-то пишет /start в чате\n3️⃣ Жми «Зарегистрироваться» — и играй!\n\n👥 Всего в боте: " + str(счёт) + " чел.\n\n👇 Добавь меня:",
                 кнопка_добавления())
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
            send(uid, "❌ Неверный пароль.")
        return
    if low == "/shop":
        send(uid, текст_магазина(uid), кнопки_магазина(uid))
        return
    if low == "/chatid":
        send(uid, "🆔 Мой chat_id: " + str(uid))
        return
    if low == "/start" and not payload:
        счёт = len([x for x in users_reg.values() if x.get("имя")])
        send(uid,
             "👋 Привет, " + u["имя"] + "!\n\nЯ — Тайный Друг 🎭\n\n📋 Как играть:\n1️⃣ Добавь меня в чат\n2️⃣ Кто-то пишет /start в чате\n3️⃣ Жми «Зарегистрироваться»\n4️⃣ Отправляй комплименты\n\n💰 Баланс: " + str(u.get("balance", 0)) + "⭐\n👥 Всего в боте: " + str(счёт) + " чел.\n\n👇 Добавь меня в чат:",
             кнопка_добавления())
        return
    if low == "/guess":
        for cid_s in u.get("чаты", []):
            cid = int(cid_s)
            c = получить_чат(cid)
            история = c.get("история", {}).get(str(uid), [])
            last = None
            for h in reversed(история):
                if not h.get("угадано"): last = h; break
            if last:
                u["_wait_guess"] = str(cid) + "_" + str(last["от"])
                save()
                варианты = [users_reg.get(int(k), {}).get("имя", "?") for k in c["игроки"] if int(k) != uid]
                send(uid, "🤔 Кто отправил последний комплимент?\n\nВарианты: " + ", ".join(варианты) + "\n\nНапиши имя.")
                return
        send(uid, "У тебя нет неразгаданных комплиментов.")
        return
    if u.get("_wait_guess"):
        parts = u["_wait_guess"].split("_")
        cid = int(parts[0])
        автор = int(parts[1])
        c = получить_чат(cid)
        имя_автора = users_reg.get(автор, {}).get("имя", "")
        история = c.get("история", {}).get(str(uid), [])
        if text.strip().lower() == имя_автора.lower():
            for h in reversed(история):
                if not h.get("угадано"): h["угадано"] = True; break
            for target_uid in (uid, автор):
                tu = users_reg.get(target_uid)
                tu["очки"] = tu.get("очки", 0) + 2
                tu["очки_всего"] = tu.get("очки_всего", 0) + 2
            users_reg[автор]["угадали"] = users_reg[автор].get("угадали", 0) + 1
            u["_wait_guess"] = None
            save()
            send(uid, "🎉 Точно! Это был(а) " + имя_автора + "! +2 очка")
            send(автор, "👀 Тебя раскрыли! +2 очка")
        else:
            au = users_reg.get(автор)
            au["очки"] = au.get("очки", 0) + 3
            au["очки_всего"] = au.get("очки_всего", 0) + 3
            u["_wait_guess"] = None
            save()
            send(uid, "❌ Не угадал. Автор остался в тайне. +3 очка автору.")
            send(автор, "😎 Ты остался загадкой! +3 очка")
        return
    if u.get("_wait_own"):
        data = u["_wait_own"]
        chat_id = data["chat"]
        кому_uid = data["to"]
        текст = text.strip()[:200]
        if текст:
            отправить_комплимент(chat_id, uid, кому_uid, текст)
        u["_wait_own"] = None
        save()
        return
    if low == "/help":
        send(uid, "📖 Команды:\n\nВ чате: кнопки в меню\n\nВ личке:\n• /guess — угадать автора\n• /shop — магазин\n• /admin — админка\n• /chatid — ID\n• /reset — сброс профиля")
        return
    send(uid, "Не понял. /start")

def обработка_группы(chat_id, uid, text):
    print("[ГРУППА] chat=" + str(chat_id) + " uid=" + str(uid) + " text=" + repr(text))
    low = text.strip().lower()
    c = получить_чат(chat_id)
    if low == "/start":
        send(chat_id, "💌 Тайный Друг\n\n🎯 Анонимные комплименты друзьям.\n\n👇 Жми:", кнопки_списка(chat_id))
        return
    if low == "/send_comp":
        send(chat_id, "💌 Жми кнопку:", кнопки_списка(chat_id))
        return
    if low == "/chatid":
        send(chat_id, "🆔 chat_id этой группы: " + str(chat_id))
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
            send(chat_id, "❌ «" + имя + "» не найден."); return
        if target == str(uid):
            send(chat_id, "😄 Себе вызов не бросить!"); return
        if str(uid) not in c["игроки"]:
            send(chat_id, "❌ Сначала зарегистрируйся!"); return
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
            send(uid, "✅ Баланс пополнен на " + str(сумма) + "⭐\n\n💰 Текущий: " + str(u["balance"]) + "⭐")
        return
    if payload == "buy_color":
        if u.get("balance", 0) < ЦЕНА_ЦВЕТ_ИМЯ:
            send(uid, "❌ Не хватает звёзд."); return
        if u.get("цветное_имя"):
            send(uid, "❌ Уже есть."); return
        u["balance"] -= ЦЕНА_ЦВЕТ_ИМЯ
        u["цветное_имя"] = True
        save()
        send(uid, "✅ Цветное имя активировано!")
        for cid_s in u.get("чаты", []):
            try: обновить_список(int(cid_s))
            except: pass
        return
    if payload == "buy_reveal":
        if u.get("balance", 0) < ЦЕНА_УЗНАТЬ_АВТОРА:
            send(uid, "❌ Не хватает звёзд."); return
        u["balance"] -= ЦЕНА_УЗНАТЬ_АВТОРА
        save()
        найдено = False
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
                    найдено = True
                    break
            if найдено: break
        if not найдено:
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
                    print("[НОВЫЙ ЧАТ] " + str(chat_id))
                    send(chat_id, "👋 Привет, ребята!\n\nЯ — Тайный Друг 🎭\n🎯 Цель: стать «Душой компании».\n\n👇 Жми Старт:",
                         kb([[("🚀 Старт", "begin")]]))
                continue
            cb = upd.get("callback_query")
            if cb:
                uid = cb["from"]["id"]
                chat_id = cb["message"]["chat"]["id"]
                act = cb["data"]
                u = получить_юзера(uid)
                if act == "begin":
                    answer_cb(cb["id"], "🚀")
                    send(chat_id, "💌 Меню:", кнопки_списка(chat_id))
                elif act == "howto_add":
                    answer_cb(cb["id"])
                    send(uid, "📖 КАК ДОБАВИТЬ БОТА В ЧАТ\n\nСпособ 1: жми «➕ Добавить в чат (кнопка)»\n\nСпособ 2 (вручную):\n• Открой группу → название → Управление → Участники → Добавить\n• Введи: @" + BOT_USERNAME + "\n\nСпособ 3: жми «📋 Скопировать @username» и вставь в поиск Telegram")
                elif act == "reg_me":
                    if not u.get("имя"):
                        answer_cb(cb["id"], "📝 Сначала /start в личке.", alert=True)
                    else:
                        c = получить_чат(chat_id)
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
                        answer_cb(cb["id"], "❌ Сначала зарегистрируйся!", alert=True)
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
                    имя_цели = чаты[real_chat]["игроки"].get(str(target_uid), "???")
                    send(uid, "Кому: " + имя_цели + "\n\nКак отправить?",
                         kb([
                             [("🎲 Случайный", "rand_" + str(real_chat) + "_" + str(target_uid))],
                             [("✍️ Свой текст", "own_" + str(real_chat) + "_" + str(target_uid))]
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
                    имя_цели = чаты[real_chat]["игроки"].get(str(target_uid), "???")
                    send(uid, "✍️ Напиши комплимент для " + имя_цели + ":")
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
                    отправить_счёт(uid, "💰 Пополнение", "Зачисление " + str(сумма) + " звёзд", "topup_" + str(сумма), сумма)
                elif act == "buy_color":
                    answer_cb(cb["id"])
                    if u.get("цветное_имя"):
                        send(uid, "❌ Уже есть.")
                    elif u.get("balance", 0) < ЦЕНА_ЦВЕТ_ИМЯ:
                        send(uid, "❌ Не хватает звёзд (" + str(u.get("balance", 0)) + "⭐). /shop")
                    else:
                        u["balance"] -= ЦЕНА_ЦВЕТ_ИМЯ
                        u["цветное_имя"] = True
                        save()
                        send(uid, "✅ Цветное имя активировано! Осталось: " + str(u["balance"]) + "⭐")
                        for cid_s in u.get("чаты", []):
                            try: обновить_список(int(cid_s))
                            except: pass
                elif act == "buy_reveal":
                    answer_cb(cb["id"])
                    if u.get("balance", 0) < ЦЕНА_УЗНАТЬ_АВТОРА:
                        send(uid, "❌ Не хватает звёзд (" + str(u.get("balance", 0)) + "⭐). /shop")
                    else:
                        u["balance"] -= ЦЕНА_УЗНАТЬ_АВТОРА
                        save()
                        найдено = False
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
                                    найдено = True
                                    break
                            if найдено: break
                        if not найдено:
                            u["balance"] += ЦЕНА_УЗНАТЬ_АВТОРА
                            save()
                            send(uid, "❌ Нет неразгаданных. Возврат.")
                elif act == "refresh":
                    answer_cb(cb["id"], "🔄")
                    send(chat_id, "📋 Список:\n\n" + текст_списка(chat_id), кнопки_списка(chat_id))
                elif act == "top":
                    answer_cb(cb["id"]); send(chat_id, топ_текст(chat_id))
                elif act == "top_all":
                    answer_cb(cb["id"]); send(chat_id, топ_всё_время(chat_id))
                elif act == "profile":
                    answer_cb(cb["id"]); send(chat_id, профиль_текст(uid))
                elif act == "duel":
                    answer_cb(cb["id"]); send(chat_id, "⚔ /duel Имя")
                elif act == "help":
                    answer_cb(cb["id"])
                    send(chat_id, "📖 Как играть:\n1. Зарегистрируйся\n2. Отправляй комплименты\n3. Угадывай автора /guess\n4. Соревнуйся в топах\n\n💎 Магазин — /shop")
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
                    for cid, c in list(чаты.items())[:20]:
                        s += "• " + str(cid) + " — " + str(len(c["игроки"])) + " игроков\n"
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
                    for cid, c in чаты.items():
                        if target_uid in c["игроки"]:
                            if значок == "❌":
                                c["значки"].pop(target_uid, None)
                                send(uid, "✅ Убран.")
                            else:
                                c["значки"][target_uid] = значок
                                send(uid, "✅ " + значок + " выдан " + c["игроки"][target_uid] + "!")
                            found = True
                            обновить_список(cid)
                            break
                    if not found:
                        send(uid, "❌ Игрок не в чате.")
                    save()
                    админ_меню(uid)
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
                payload = msg["successful_payment"]["invoice_payload"]
                print("[ОПЛАТА] uid=" + str(uid) + " payload=" + payload)
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
