import requests
import http.server
import socketserver
import time
import json
import os
import random
import threading

TOKEN = "8918941174:AAE6VYeW4cPTsGInySM0W_4J1Dq6XmpPO4M"
API = "https://api.telegram.org/bot" + TOKEN
SAVE_FILE = "secret_friend.json"
offset = 0

ADMIN_PASSWORD = "12345"

users_reg = {}   # {uid: {"имя": ..., "очки": ..., "чаты": [chat_id, ...]}}
чаты = {}        # {chat_id: {...}}
BOT_USERNAME = "Tajnij_dryg_bot"

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

ЗНАЧКИ = {"👑": "Главный админ", "🛡": "Помощник", "⭐": "Проверенный", "🧪": "Тестировщик"}

# ============ TELEGRAM ============
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

# ============ ЗАГРУЗКА ============
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
            чаты = {}; users_reg = {}

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
    return {"игроки": {}, "ожидание": {}, "история": {},
            "список_msg_id": None, "дуэли": [], "значки": {}}

def получить_чат(cid):
    c = чаты.get(cid)
    if not c:
        c = новый_чат(); чаты[cid] = c
    if "значки" not in c: c["значки"] = {}
    if "дуэли" not in c: c["дуэли"] = []
    if "история" not in c: c["история"] = {}
    return c

def получить_юзера(uid):
    u = users_reg.get(uid)
    if not u:
        u = {"имя": None, "очки": 0, "очки_всего": 0, "чаты": [],
             "получено": 0, "отправлено": 0, "угадали": 0}
        users_reg[uid] = u
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

# ============ СПИСОК ЧАТА ============
def кнопки_списка(chat_id):
    return kb([
        [("📝 Зарегистрироваться", "reg_me")],
        [("👥 Список участников", "refresh")],
        [("🏆 Топ недели", "top")],
        [("🌍 Топ за всё время", "top_all")],
        [("👤 Мой профиль", "profile")],
        [("⚔ Дуэль", "duel")],
        [("❓ Помощь", "help")]
    ])

def текст_списка(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "👥 Участники\n\nПока никто не зарегистрирован.\n\n📝 Жми «Зарегистрироваться»!"
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки", 0))
    s = f"👥 Участники ({len(sp)}):\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, имя) in enumerate(sp):
        u = users_reg.get(int(uid), {})
        знак = значок_игрока(uid)
        префикс = f"{знак} " if знак else ""
        m = medals[i] if i < 3 else f"{i+1}."
        s += f"{m} {префикс}{имя} — {u.get('очки', 0)} очк.\n"
    s += "\n📝 /send_comp — комплимент\n⚔ /duel Имя — дуэль"
    return s

def топ_текст(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "🏆 Топ недели\n\nПока никого."
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки", 0))[:10]
    s = "🏆 Топ недели:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, имя) in enumerate(sp):
        u = users_reg.get(int(uid), {})
        знак = значок_игрока(uid)
        префикс = f"{знак} " if знак else ""
        m = medals[i] if i < 3 else f"{i+1}."
        s += f"{m} {префикс}{имя} — {u.get('очки', 0)} очк. [{звание(u.get('очки', 0))}]\n"
    return s

def топ_всё_время(chat_id):
    c = получить_чат(chat_id)
    if not c["игроки"]:
        return "🌍 Топ за всё время\n\nПока никого."
    sp = sorted(c["игроки"].items(), key=lambda x: -users_reg.get(int(x[0]), {}).get("очки_всего", 0))[:10]
    s = "🌍 Топ за всё время:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, имя) in enumerate(sp):
        u = users_reg.get(int(uid), {})
        знак = значок_игрока(uid)
        префикс = f"{знак} " if знак else ""
        m = medals[i] if i < 3 else f"{i+1}."
        s += f"{m} {префикс}{имя} — {u.get('очки_всего', 0)} очк.\n"
    return s

def профиль_текст(uid):
    u = users_reg.get(uid)
    if not u or not u.get("имя"):
        return "❌ Ты не зарегистрирован."
    знак = значок_игрока(uid)
    имя_с_значком = f"{знак} {u['имя']}" if знак else u['имя']
    return (f"👤 Профиль: {имя_с_значком}\n\n"
            f"🏆 Очки (неделя): {u.get('очки', 0)}\n"
            f"🌍 Очки (всего): {u.get('очки_всего', 0)}\n"
            f"🎖 Звание: {звание(u.get('очки_всего', 0))}\n\n"
            f"💌 Отправлено: {u.get('отправлено', 0)}\n"
            f"📥 Получено: {u.get('получено', 0)}\n"
            f"🎯 Угадали тебя: {u.get('угадали', 0)} раз")

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
        try: api("pinChatMessage", {"chat_id": chat_id, "message_id": msg_id, "disable_notification": True})
        except: pass

# ============ ДУЭЛИ ============
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
            send(chat_id, f"⚔ ДУЭЛЬ ЗАВЕРШЕНА!\n\n{имя1} vs {имя2}\n📊 {d['очки1']} : {d['очки2']}\n\n🏆 Победитель: {u['имя']} — +20 очков!")
            send(int(поб), "🎉 Ты выиграл дуэль! +20 очков")
        else:
            send(chat_id, f"⚔ ДУЭЛЬ ЗАВЕРШЕНА!\n\n{имя1} vs {имя2}\n📊 {d['очки1']} : {d['очки2']}\n\n🤝 Ничья!")
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

# ============ АДМИН ============
admin_session = {}

def админ_меню(uid):
    счёт = len([u for u in users_reg.values() if u.get("имя")])
    send(uid,
         f"👑 АДМИН-МЕНЮ\n\n"
         f"👥 Всего зарегистрировано в боте: {счёт}\n\n"
         f"Выбери действие:",
         {"inline_keyboard": [
             [{"text": "📊 Все пользователи", "callback_data": "admin_users"}],
             [{"text": "🎖 Выдать значок", "callback_data": "admin_icon"}],
             [{"text": "❌ Закрыть", "callback_data": "admin_close"}]
         ]})

def меню_значков(target_uid):
    return {"inline_keyboard": [
        [{"text": "👑 Главный админ", "callback_data": f"seticon_👑_{target_uid}"}],
        [{"text": "🛡 Помощник", "callback_data": f"seticon_🛡_{target_uid}"}],
        [{"text": "⭐ Проверенный", "callback_data": f"seticon_⭐_{target_uid}"}],
        [{"text": "🧪 Тестировщик", "callback_data": f"seticon_🧪_{target_uid}"}],
        [{"text": "❌ Убрать значок", "callback_data": f"seticon_❌_{target_uid}"}],
        [{"text": "↩ Назад", "callback_data": "admin_back"}]
    ]}

# ============ ЛИЧКА ============
def обработка_лички(uid, text, payload=None):
    low = text.strip().lower()
    u = получить_юзера(uid)

    # --- Регистрация (шаг 1 или 2) ---
    if u.get("имя") is None:
        if low == "/start" or payload:
            send(uid,
                 "👋 Привет! Я — Тайный Друг 🎭\n\n"
                 "Помогаю отправлять анонимные комплименты друзьям.\n\n"
                 "📝 Как тебя зовут? Напиши своё имя:")
            return
        # ждём имя
        if not text.startswith("/"):
            имя = text.strip()[:20]
            u["имя"] = имя
            save()
            send(uid,
                 f"✅ Отлично, {имя}!\n\n"
                 f"🎯 Что дальше:\n"
                 f"1️⃣ Добавь меня в чат с друзьями\n"
                 f"2️⃣ Кто-то пишет /start в чате\n"
                 f"3️⃣ Регистрируйся — и отправляй комплименты!\n\n"
                 f"👥 Всего в боте: {len([x for x in users_reg.values() if x.get('имя')])} чел.",
                 kb([[("➕ Добавить в чат", f"https://t.me/{BOT_USERNAME}?startgroup=true")]]))
            return

    # --- Админ ---
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

    # --- Deep-link (комплимент/реферал/регистрация в чате) ---
    if payload:
        if payload.startswith("reg_"):
            chat_id = int(payload.replace("reg_", ""))
            c = получить_чат(chat_id)
            c["игроки"][str(uid)] = u["имя"]
            if chat_id not in u["чаты"]:
                u["чаты"].append(chat_id)
            save()
            send(uid, f"✅ Ты зарегистрирован в чате {chat_id}!")
            обновить_список(chat_id)
            return
        if payload.startswith("comp_"):
            chat_id = int(payload.replace("comp_", ""))
            c = получить_чат(chat_id)
            c["ожидание"][str(uid)] = f"comp_{chat_id}"
            save()
            send(uid, "💌 Напиши имя того, кому хочешь отправить комплимент:")
            return
        if payload.startswith("ref_"):
            parts = payload.split("_")
            chat_id = int(parts[1]); реферер = int(parts[2])
            c = получить_чат(chat_id)
            c["игроки"][str(uid)] = u["имя"]
            if chat_id not in u["чаты"]:
                u["чаты"].append(chat_id)
            if реферер in users_reg:
                ru = users_reg[реферер]
                ru["очки"] = ru.get("очки", 0) + 5
                ru["очки_всего"] = ru.get("очки_всего", 0) + 5
                send(реферер, "🎉 По твоей ссылке пришёл друг! +5 очков")
            save()
            send(uid, f"✅ Ты зарегистрирован в чате {chat_id}!")
            обновить_список(chat_id)
            return

    if low == "/start" and not payload:
        send(uid,
             f"👋 Привет, {u['имя']}!\n\n"
             f"Я — Тайный Друг 🎭\n\n"
             f"📋 Как играть:\n"
             f"1️⃣ Добавь меня в чат\n2️⃣ Кто-то пишет /start\n3️⃣ Регистрируйся\n"
             f"4️⃣ Отправляй комплименты\n\n"
             f"👥 Всего в боте: {len([x for x in users_reg.values() if x.get('имя')])} чел.\n"
             f"Твои чаты: {len(u.get('чаты', []))}\n\n"
             f"👇 Добавь меня в чат:",
             kb([[("➕ Добавить в чат", f"https://t.me/{BOT_USERNAME}?startgroup=true")]]))
        return

    if low == "/guess":
        # ищем последний неразгаданный
        for cid_s in u.get("чаты", []):
            cid = int(cid_s)
            c = получить_чат(cid)
            история = c.get("история", {}).get(str(uid), [])
            last = None
            for h in reversed(история):
                if not h.get("угадано"): last = h; break
            if last:
                u["_wait_guess"] = f"{cid}_{last['от']}"
                save()
                варианты = [users_reg.get(int(k), {}).get("имя", "?") for k in c["игроки"] if int(k) != uid]
                send(uid, f"🤔 Кто отправил последний комплимент?\n\nВарианты: {', '.join(варианты)}\n\nНапиши имя.")
                return
        send(uid, "У тебя нет неразгаданных комплиментов.")
        return

    if u.get("_wait_guess"):
        parts = u["_wait_guess"].split("_")
        cid = int(parts[0]); автор = int(parts[1])
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
            send(uid, f"🎉 Точно! Это был(а) {имя_автора}! +2 очка")
            send(автор, f"👀 Тебя раскрыли! +2 очка")
        else:
            au = users_reg.get(автор)
            au["очки"] = au.get("очки", 0) + 3
            au["очки_всего"] = au.get("очки_всего", 0) + 3
            u["_wait_guess"] = None
            save()
            send(uid, "❌ Не угадал. Автор остался в тайне. +3 очка автору.")
            send(автор, "😎 Ты остался загадкой! +3 очка")
        return

    if low == "/help":
        send(uid, "📖 Команды:\n\nВ чате:\n• /send_comp\n• /duel Имя\n• /players\n\nВ личке:\n• /guess\n• /admin")
        return

    # --- ожидания чата (комплимент) ---
    for cid, c in чаты.items():
        ожидание = c.get("ожидание", {}).get(str(uid))
        if not ожидание: continue

        if ожидание.startswith("comp_"):
            target_uid = None
            for k, имя in c["игроки"].items():
                if имя.lower() == text.strip().lower():
                    target_uid = int(k); break
            if not target_uid:
                send(uid, f"❌ «{text.strip()}» не найден.")
                del c["ожидание"][str(uid)]; save(); return
            if target_uid == uid:
                send(uid, "😄 Себе комплимент не отправить!")
                del c["ожидание"][str(uid)]; save(); return
            c["ожидание"][str(uid)] = f"choose_{cid}_{target_uid}"; save()
            send(uid, f"Кому: {c['игроки'][str(target_uid)]}\n\nКак отправить?",
                 kb([
                     [("🎲 Случайный", f"rand_{cid}_{target_uid}")],
                     [("✍️ Написать свой", f"own_{cid}_{target_uid}")]
                 ]))
            return

        if ожидание.startswith("ownmsg_"):
            parts = ожидание.split("_")
            chat_id = int(parts[1]); target_uid = parts[2]
            текст_комплимента = text.strip()[:200]
            if not текст_комплимента:
                send(uid, "❌ Пустой комплимент."); return
            u["очки"] = u.get("очки", 0) + 1
            u["очки_всего"] = u.get("очки_всего", 0) + 1
            u["отправлено"] = u.get("отправлено", 0) + 1
            tu = users_reg.get(int(target_uid))
            if tu: tu["получено"] = tu.get("получено", 0) + 1
            c["история"].setdefault(str(target_uid), [])
            c["история"][str(target_uid)].append({"от": uid, "текст": текст_комплимента, "угадано": False})
            учесть_комплимент_в_дуэли(chat_id, int(target_uid))
            del c["ожидание"][str(uid)]; save()
            send(uid, "✅ Комплимент отправлен! +1 очко")
            send(int(target_uid), f"💌 Тебе анонимный комплимент:\n\n«{текст_комплимента}»\n\nХочешь угадать? /guess")
            return

    send(uid, "Не понял. /start")

# ============ ГРУППА ============
def обработка_группы(chat_id, uid, text):
    print(f"[ГРУППА] chat={chat_id} uid={uid} text={text!r}")
    low = text.strip().lower()
    c = получить_чат(chat_id)

    if low == "/start":
        send(chat_id,
             "💌 Тайный Друг\n\n🎯 Анонимные комплименты друзьям.\n"
             "🏆 Цель: стать «Душой компании».\n\n👇 Жми:",
             кнопки_списка(chat_id))
        return

    if low == "/send_comp":
        url = f"https://t.me/{BOT_USERNAME}?start=comp_{chat_id}"
        send(chat_id, "💌 Жми кнопку:",
             kb([[("💌 Отправить комплимент", url)]]))
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
            send(chat_id, f"❌ «{имя}» не найден."); return
        if target == str(uid):
            send(chat_id, "😄 Себе вызов не бросить!"); return
        if str(uid) not in c["игроки"]:
            send(chat_id, "❌ Сначала /start"); return
        for d in c["дуэли"]:
            if d.get("завершена"): continue
            if str(uid) in (d["игрок1"], d["игрок2"]) or target in (d["игрок1"], d["игрок2"]):
                send(chat_id, "❌ Один из вас уже в дуэли."); return
        создать_дуэль(chat_id, int(uid), int(target))
        имя1 = c["игроки"][str(uid)]; имя2 = c["игроки"][target]
        send(chat_id, f"⚔ ДУЭЛЬ!\n\n{имя1} vs {имя2}\n\n📊 За 24 часа больше комплиментов.\n🏆 Победитель: +20 очков!")
        return

    if low == "/players":
        send(chat_id, текст_списка(chat_id), кнопки_списка(chat_id)); return

    if low == "/help":
        send(chat_id, "📖 Команды:\n/start — меню\n/send_comp — комплимент\n/duel Имя — дуэль\n/players — список")
        return

# ============ ЗАПУСК ============
load()
# ============ Веб-сервер для Render ============
def запустить_веб_сервер():
    port = int(os.environ.get("PORT", 10000))
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is alive")
        def log_message(self, *args):
            pass
    try:
        with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print("Веб-сервер:", e)

threading.Thread(target=запустить_веб_сервер, daemon=True).start()
print(f"Бот запущен: @{BOT_USERNAME}")

while True:
    try:
        r = requests.get(API + "/getUpdates",
                         params={"offset": offset, "timeout": 20,
                                 "allowed_updates": '["message","callback_query","my_chat_member"]'},
                         timeout=25)
        data = r.json()
        if not data.get("ok"):
            print("Err:", data); time.sleep(2); continue

        for upd in data["result"]:
            offset = upd["update_id"] + 1

            mcm = upd.get("my_chat_member")
            if mcm:
                chat = mcm["chat"]; new_status = mcm["new_chat_member"]["status"]; chat_id = chat["id"]
                if chat_id < 0 and new_status in ("member", "administrator"):
                    получить_чат(chat_id)
                    send(chat_id,
                         "👋 Привет, ребята!\n\nЯ — Тайный Друг 🎭\n"
                         "🎯 Цель: стать «Душой компании».\n\n👇 Жми:",
                         kb([[("🚀 Старт", "begin")]]))
                continue

            cb = upd.get("callback_query")
            if cb:
                uid = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]; act = cb["data"]

                if act == "begin":
                    answer_cb(cb["id"], "🚀 Поехали!")
                    send(chat_id, "💌 Меню:", кнопки_списка(chat_id))
                elif act == "reg_me":
                    u = получить_юзера(uid)
                    if not u.get("имя"):
                        answer_cb(cb["id"], f"📝 Сначала напиши мне в личку: @{BOT_USERNAME}\n\nНажми там /start и введи имя.", alert=True)
                    else:
                        answer_cb(cb["id"], "✅ Зарегистрирован!")
                        c = получить_чат(chat_id)
                        c["игроки"][str(uid)] = u["имя"]
                        if chat_id not in u["чаты"]:
                            u["чаты"].append(chat_id)
                        save()
                        send(chat_id, f"✅ {u['имя']} зарегистрирован в этом чате!")
                        обновить_список(chat_id)
                    continue
                elif act == "refresh":
                    answer_cb(cb["id"], "🔄 Обновляю...")
                    send(chat_id, "📋 Список участников:\n\n" + текст_списка(chat_id), кнопки_списка(chat_id))
                elif act == "top":
                    answer_cb(cb["id"]); send(chat_id, топ_текст(chat_id))
                elif act == "top_all":
                    answer_cb(cb["id"]); send(chat_id, топ_всё_время(chat_id))
                elif act == "profile":
                    answer_cb(cb["id"]); send(chat_id, профиль_текст(uid))
                elif act == "duel":
                    answer_cb(cb["id"]); send(chat_id, "⚔ Напиши: /duel Имя")
                elif act == "help":
                    answer_cb(cb["id"])
                    send(chat_id, "📖 Как играть:\n1. /start — регистрация\n2. /send_comp — комплимент\n3. /guess — угадать автора\n4. /duel Имя — дуэль\n\n🏆 +1 отправил, +2 угадал, +3 не угадали, +20 дуэль")

                # === КОМПЛИМЕНТЫ ===
                elif act.startswith("rand_"):
                    answer_cb(cb["id"], "🎲")
                    parts = act.split("_")
                    cid = int(parts[1]); target_uid = int(parts[2])
                    c = получить_чат(cid)
                    комплимент = random.choice(КОМПЛИМЕНТЫ)
                    u = получить_юзера(uid)
                    u["очки"] = u.get("очки", 0) + 1
                    u["очки_всего"] = u.get("очки_всего", 0) + 1
                    u["отправлено"] = u.get("отправлено", 0) + 1
                    tu = получить_юзера(target_uid)
                    tu["получено"] = tu.get("получено", 0) + 1
                    c["история"].setdefault(str(target_uid), [])
                    c["история"][str(target_uid)].append({"от": uid, "текст": комплимент, "угадано": False})
                    учесть_комплимент_в_дуэли(cid, target_uid)
                    c["ожидание"].pop(str(uid), None); save()
                    send(uid, "✅ Комплимент отправлен! +1 очко")
                    send(target_uid, f"💌 Тебе анонимный комплимент:\n\n«{комплимент}»\n\nХочешь угадать? /guess")

                elif act.startswith("own_"):
                    answer_cb(cb["id"])
                    parts = act.split("_")
                    cid = int(parts[1]); target_uid = parts[2]
                    c = получить_чат(cid)
                    c["ожидание"][str(uid)] = f"ownmsg_{cid}_{target_uid}"; save()
                    send(uid, f"✍️ Напиши свой комплимент для {c['игроки'].get(target_uid, '???')}:")

                # === АДМИН ===
                elif act == "admin_users":
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    если = [u for u in users_reg.values() if u.get("имя")]
                    if not если:
                        send(uid, "Никто не зарегистрирован."); continue
                    s = f"👥 Всего в боте: {len(если)}\n\n"
                    for i, uu in enumerate(если[:30], 1):
                        знак = значок_игрока(list(users_reg.keys())[list(users_reg.values()).index(uu)]) if False else ""
                        s += f"{i}. {uu['имя']} — {uu.get('очки_всего', 0)} очк.\n"
                    send(uid, s)
                elif act == "admin_icon":
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    если = [(k, u) for k, u in users_reg.items() if u.get("имя")]
                    if not если:
                        send(uid, "Никто не зарегистрирован."); continue
                    rows = []
                    for uu_id, uu in если[:20]:
                        rows.append([{"text": uu["имя"], "callback_data": f"pickuser_{uu_id}"}])
                    send(uid, "Кому выдать значок?", {"inline_keyboard": rows})
                elif act.startswith("pickuser_"):
                    answer_cb(cb["id"])
                    if not admin_session.get(uid): continue
                    target_uid = act.replace("pickuser_", "")
                    имя = users_reg.get(int(target_uid), {}).get("имя", "???")
                    send(uid, f"Выбери значок для {имя}:", меню_значков(target_uid))
                elif act.startswith("seticon_"):
                    parts = act.split("_")
                    значок = parts[1]; target_uid = parts[2]
                    if not admin_session.get(uid): continue
                    # находим чат, где этот юзер есть, и ставим значок
                    found = False
                    for c in чаты.values():
                        if target_uid in c["игроки"]:
                            if значок == "❌":
                                c["значки"].pop(target_uid, None)
                                send(uid, "✅ Значок убран.")
                            else:
                                c["значки"][target_uid] = значок
                                send(uid, f"✅ {значок} выдан {c['игроки'][target_uid]}!")
                            found = True
                            обновить_список(int(list(чаты.keys())[list(чаты.values()).index(c)]))
                            break
                    if not found:
                        send(uid, "❌ Игрок не в чате.")
                    save()
                    админ_меню(uid)
                elif act == "admin_back":
                    answer_cb(cb["id"])
                    админ_меню(uid)
                elif act == "admin_close":
                    answer_cb(cb["id"], "Закрыто")
                    admin_session.pop(uid, None)
                else:
                    answer_cb(cb["id"])
                continue

            msg = upd.get("message")
            if not msg: continue
            chat_id = msg["chat"]["id"]; uid = msg["from"]["id"]; text = msg.get("text") or ""

            payload = None
            if text.startswith("/start "):
                payload = text.split(maxsplit=1)[1]; text = "/start"

            if chat_id > 0:
                обработка_лички(uid, text, payload)
            else:
                if text:
                    обработка_группы(chat_id, uid, text)

    except Exception as e:
        print("Ошибка:", e); time.sleep(3)
