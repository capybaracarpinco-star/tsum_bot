import telebot
from telebot import types
import os, json, time
 
bot = telebot.TeleBot("8916062839:AAF1x1rICohL4pjYqBpMxJZ6r9d2_mzGeuA")  # ←← ВСТАВЬ ТОКЕН
 
ADMINS = [2122741678, 5575071175]
 
items, orders, services, active_chats = {}, {}, {}, {}
cooldowns = {}
 
def load(f, default):
    try: return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else default
    except: return default
 
def save(f, data):
    json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
 
items    = load("items.json", {})
orders   = load("orders.json", {})
services = load("services.json", {})
 
def is_admin(uid): return uid in ADMINS
 
def main_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛒 Купить", "📦 Наличие")
    kb.add("💎 Премиальные услуги", "⭐️ Отзывы")
    if is_admin(uid): kb.add("⚙️ Админка")
    return kb
 
def save_user(uid):
    if is_admin(uid): return
    users = set()
    if os.path.exists("users.txt"):
        users = set(int(l.strip()) for l in open("users.txt") if l.strip())
    users.add(uid)
    open("users.txt", "w").write("\n".join(str(u) for u in users))


def check_cooldown(uid):
    """Проверка анти-спама: 1 заказ раз в 5 минут"""
    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < 300:  # 5 минут = 300 секунд
        remaining = int(300 - (now - cooldowns[uid]))
        return False, remaining
    cooldowns[uid] = now
    return True, 0


def edit_menu(uid, category="items"):
    data = items if category == "items" else services
    prefix = "edit_" if category == "items" else "editsvc_"
    add_cb = "add_item" if category == "items" else "add_svc"
    title = "🛠 Управление товарами:" if category == "items" else "💎 Управление услугами:"
    kb = types.InlineKeyboardMarkup(row_width=1)
    for k, v in data.items():
        s = "✅" if v.get("available", True) else "❌"
        kb.add(types.InlineKeyboardButton(f"{s} {v['name']} — {v['price']}", callback_data=f"{prefix}{k}"))
    kb.add(types.InlineKeyboardButton("➕ Добавить", callback_data=add_cb))
    bot.send_message(uid, title, reply_markup=kb)
 
# ── СТАРТ ──
@bot.message_handler(commands=["start"])
def start(m):
    save_user(m.chat.id)
    bot.send_message(m.chat.id, "👋 Добро пожаловать в магазин Roblox Tsum!", reply_markup=main_kb(m.chat.id))
 
# ── ПОКУПКА ──
@bot.message_handler(func=lambda m: m.text == "🛒 Купить")
def buy(m):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for k, v in items.items():
        if v.get("available", True):
            kb.add(types.InlineKeyboardButton(f"{v['name']} — {v['price']}", callback_data=f"buy_{k}"))
    bot.send_message(m.chat.id, "🎁 Выберите товар:" if kb.keyboard else "Товаров нет в наличии.", reply_markup=kb or None)
 
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_") and not c.data.startswith("buy_svc_"))
def buy_cb(c):
    key = c.data[4:]
    if key not in items: return bot.answer_callback_query(c.id, "Товар не найден.")
    item = items[key]

    allowed, remaining = check_cooldown(c.from_user.id)
    if not allowed:
        bot.answer_callback_query(c.id, f"⏳ Подожди {remaining} сек. перед новым заказом", show_alert=True)
        return

    oid = str(len(orders) + 1).zfill(3)
    orders[oid] = {"user_id": c.from_user.id, "username": c.from_user.username, "item": item["name"], "price": item["price"], "type": "item"}
    save("orders.json", orders)
    bot.send_message(c.message.chat.id,
        f"🛍 *Заказ \#{oid}*\nТовар: *{item['name']}* — {item['price']}\n\n"
        f"⏳ Ожидайте, администрация примется за ваш заказ.", parse_mode="Markdown")
    for a in ADMINS:
        bot.send_message(a, f"🛒 *Новый заказ \#{oid}*\nТовар: {item['name']}\nПокупатель: @{c.from_user.username or 'нет'}", parse_mode="Markdown")
    bot.answer_callback_query(c.id)
 
# ── ПРЕМИАЛЬНЫЕ УСЛУГИ ──
@bot.message_handler(func=lambda m: m.text == "💎 Премиальные услуги")
def show_services(m):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for k, v in services.items():
        if v.get("available", True):
            kb.add(types.InlineKeyboardButton(f"{v['name']} — {v['price']}", callback_data=f"buy_svc_{k}"))
    bot.send_message(m.chat.id, "💎 Премиальные услуги:" if kb.keyboard else "Услуг пока нет.", reply_markup=kb or None)
 
@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_svc_"))
def buy_svc_cb(c):
    key = c.data[8:]
    if key not in services: return bot.answer_callback_query(c.id, "Услуга не найдена.")
    svc = services[key]

    allowed, remaining = check_cooldown(c.from_user.id)
    if not allowed:
        bot.answer_callback_query(c.id, f"⏳ Подожди {remaining} сек. перед новым заказом", show_alert=True)
        return

    oid = str(len(orders) + 1).zfill(3)
    orders[oid] = {"user_id": c.from_user.id, "username": c.from_user.username, "item": svc["name"], "price": svc["price"], "type": "service"}
    save("orders.json", orders)
    bot.send_message(c.message.chat.id,
        f"💎 *Заказ \#{oid}*\nУслуга: *{svc['name']}* — {svc['price']}\n\n"
        f"⏳ Ожидайте, администрация примется за ваш заказ.", parse_mode="Markdown")
    for a in ADMINS:
        bot.send_message(a, f"💎 *Новый заказ услуги \#{oid}*\nУслуга: {svc['name']}\nПокупатель: @{c.from_user.username or 'нет'}", parse_mode="Markdown")
    bot.answer_callback_query(c.id)
 
# ── НАЛИЧИЕ ──
@bot.message_handler(func=lambda m: m.text == "📦 Наличие")
def stock(m):
    if not items: return bot.send_message(m.chat.id, "Товаров пока нет.")
    text = "📦 *В наличии:*\n\n" + "\n".join(
        f"{'✅' if v.get('available', True) else '❌'} {v['name']} — {v['price']}" for v in items.values())
    bot.send_message(m.chat.id, text, parse_mode="Markdown")
 
# ── ОТЗЫВЫ ──
@bot.message_handler(func=lambda m: m.text == "⭐️ Отзывы")
def reviews(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Перейти к отзывам", url="https://t.me/otttttttzuv"))
    bot.send_message(m.chat.id, "⭐️ Отзывы наших покупателей:", reply_markup=kb)
 
# ── АДМИНКА ──
@bot.message_handler(func=lambda m: m.text == "⚙️ Админка")
def admin(m):
    if not is_admin(m.chat.id): return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("📢 Рассылка", "📋 Заказы", "👥 Пользователи")
    kb.add("✏️ Товары", "💎 Ред. услуги", "🔙 Меню")
    bot.send_message(m.chat.id, "⚙️ Админ панель:", reply_markup=kb)
 
@bot.message_handler(func=lambda m: m.text == "🔙 Меню")
def back(m): bot.send_message(m.chat.id, "Главное меню:", reply_markup=main_kb(m.chat.id))
 
@bot.message_handler(func=lambda m: m.text == "👥 Пользователи")
def users(m):
    if not is_admin(m.chat.id): return
    try:
        count = len(set(l.strip() for l in open("users.txt") if l.strip()))
        bot.send_message(m.chat.id, f"👥 Пользователей: *{count}*", parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "Пока нет пользователей.")
 
@bot.message_handler(func=lambda m: m.text == "📋 Заказы")
def show_orders(m):
    if not is_admin(m.chat.id): return
    if not orders: return bot.send_message(m.chat.id, "Заказов нет.")
    kb = types.InlineKeyboardMarkup(row_width=1)
    for oid, d in list(orders.items())[-20:]:
        nick = f"@{d.get('username','')}" if d.get("username") else "Без ника"
        icon = "💎" if d.get("type") == "service" else "🛒"
        kb.add(types.InlineKeyboardButton(f"{icon} #{oid} | {d.get('item','?')} | {nick}", callback_data=f"chat_{d['user_id']}_{oid}"))
    bot.send_message(m.chat.id, "📋 Заказы:", reply_markup=kb)
 
@bot.message_handler(func=lambda m: m.text == "📢 Рассылка")
def broadcast(m):
    if not is_admin(m.chat.id): return
    msg = bot.send_message(m.chat.id, "Отправьте текст или фото:")
    bot.register_next_step_handler(msg, do_broadcast)
 
def do_broadcast(m):
    if not is_admin(m.chat.id): return
    try:
        uids = set(int(l.strip()) for l in open("users.txt") if l.strip())
        sent = 0
        for uid in uids:
            try:
                if m.text: bot.send_message(uid, m.text)
                elif m.photo: bot.send_photo(uid, m.photo[-1].file_id, caption=m.caption)
                sent += 1
            except: pass
        bot.send_message(m.chat.id, f"✅ Отправлено: {sent}")
    except: bot.send_message(m.chat.id, "❌ Нет пользователей.")
 
# ── ЧАТ ──
@bot.callback_query_handler(func=lambda c: c.data.startswith("chat_"))
def open_chat(c):
    if not is_admin(c.from_user.id): return
    parts = c.data[5:].split("_")
    uid, oid = int(parts[0]), parts[1] if len(parts) > 1 else "??"
    active_chats[c.from_user.id] = {"partner": uid, "order_id": oid}
    active_chats[uid] = {"partner": c.from_user.id, "order_id": oid}
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✅ Заказ выполнен", "❌ Заказ не выполнен")
    kb.add("🚪 Покинуть чат")
    bot.send_message(c.from_user.id, f"✅ Чат по заказу #{oid} открыт. Пишите сообщения:", reply_markup=kb)
    bot.send_message(uid, "👨‍💼 Администратор взялся за ваш заказ! Ожидайте.")
    bot.answer_callback_query(c.id)
 
@bot.message_handler(func=lambda m: m.text == "✅ Заказ выполнен")
def order_done(m):
    if not is_admin(m.chat.id) or m.chat.id not in active_chats: return
    partner = active_chats[m.chat.id]["partner"]
    active_chats.pop(m.chat.id, None)
    active_chats.pop(partner, None)
    bot.send_message(partner, "✅ Ваш заказ прошёл успешно! Администрация покинула заказ. Спасибо за покупку 🎉")
    bot.send_message(m.chat.id, "✅ Заказ отмечен как выполненный.", reply_markup=main_kb(m.chat.id))
 
@bot.message_handler(func=lambda m: m.text == "❌ Заказ не выполнен")
def order_fail(m):
    if not is_admin(m.chat.id) or m.chat.id not in active_chats: return
    partner = active_chats[m.chat.id]["partner"]
    active_chats.pop(m.chat.id, None)
    active_chats.pop(partner, None)
    bot.send_message(partner, "❌ К сожалению, заказ не прошёл успешно. Администрация покинула заказ.")
    bot.send_message(m.chat.id, "❌ Заказ отмечен как невыполненный.", reply_markup=main_kb(m.chat.id))
 
@bot.message_handler(func=lambda m: m.text == "🚪 Покинуть чат")
def leave(m):
    if m.chat.id in active_chats:
        partner = active_chats[m.chat.id]["partner"]
        active_chats.pop(m.chat.id, None)
        active_chats.pop(partner, None)
        bot.send_message(partner, "Администрация покинула заказ.")
    bot.send_message(m.chat.id, "✅ Вышли из чата.", reply_markup=main_kb(m.chat.id))
 
# ── ТОВАРЫ ──
@bot.message_handler(func=lambda m: m.text == "✏️ Товары")
def edit_items(m):
    if not is_admin(m.chat.id): return
    edit_menu(m.chat.id, "items")
 
@bot.message_handler(func=lambda m: m.text == "💎 Ред. услуги")
def edit_svcs(m):
    if not is_admin(m.chat.id): return
    edit_menu(m.chat.id, "services")
 
# -- Добавить товар --
@bot.callback_query_handler(func=lambda c: c.data == "add_item")
def add_item(c):
    if not is_admin(c.from_user.id): return
    bot.answer_callback_query(c.id)
    msg = bot.send_message(c.from_user.id, "Введите название товара:")
    bot.register_next_step_handler(msg, lambda m: get_name(m, "items"))
 
# -- Добавить услугу --
@bot.callback_query_handler(func=lambda c: c.data == "add_svc")
def add_svc(c):
    if not is_admin(c.from_user.id): return
    bot.answer_callback_query(c.id)
    msg = bot.send_message(c.from_user.id, "Введите название услуги:")
    bot.register_next_step_handler(msg, lambda m: get_name(m, "services"))
 
def get_name(m, category):
    if not is_admin(m.chat.id): return
    name = m.text.strip()
    msg = bot.send_message(m.chat.id, f"Название: {name}\nВведите цену:")
    bot.register_next_step_handler(msg, lambda x: get_price(x, name, category))
 
def get_price(m, name, category):
    if not is_admin(m.chat.id): return
    data = items if category == "items" else services
    fname = "items.json" if category == "items" else "services.json"
    key = name.lower().replace(" ", "_")[:30]
    data[key] = {"name": name, "price": m.text.strip(), "available": True}
    save(fname, data)
    bot.send_message(m.chat.id, f"✅ Добавлено: «{name}»!")
    edit_menu(m.chat.id, category)
 
# -- Редактировать товар --
@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_") and not c.data.startswith("editsvc_"))
def edit_item(c):
    if not is_admin(c.from_user.id): return
    key = c.data[5:]
    if key not in items: return
    _send_edit_buttons(c, key, "items")
 
# -- Редактировать услугу --
@bot.callback_query_handler(func=lambda c: c.data.startswith("editsvc_"))
def edit_svc(c):
    if not is_admin(c.from_user.id): return
    key = c.data[8:]
    if key not in services: return
    _send_edit_buttons(c, key, "services")
 
def _send_edit_buttons(c, key, category):
    p = "i" if category == "items" else "s"
    data = items if category == "items" else services
    item = data[key]
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✏️ Название", callback_data=f"cn_{p}_{key}"),
        types.InlineKeyboardButton("💰 Цена",     callback_data=f"cp_{p}_{key}"),
        types.InlineKeyboardButton("✅/❌ Наличие", callback_data=f"tg_{p}_{key}"),
        types.InlineKeyboardButton("🗑 Удалить",   callback_data=f"dl_{p}_{key}")
    )
    bot.send_message(c.from_user.id, f"*{item['name']}* — {item['price']}", reply_markup=kb, parse_mode="Markdown")
    bot.answer_callback_query(c.id)
 
def _get_cat(p): return ("items", "items.json") if p == "i" else ("services", "services.json")
def _get_data(p): return items if p == "i" else services
 
@bot.callback_query_handler(func=lambda c: c.data.startswith("tg_"))
def toggle(c):
    if not is_admin(c.from_user.id): return
    _, p, key = c.data.split("_", 2)
    data = _get_data(p)
    cat, fname = _get_cat(p)
    if key in data:
        data[key]["available"] = not data[key].get("available", True)
        save(fname, data)
    bot.answer_callback_query(c.id, "Статус изменён")
    edit_menu(c.from_user.id, cat)
 
@bot.callback_query_handler(func=lambda c: c.data.startswith("dl_"))
def delete(c):
    if not is_admin(c.from_user.id): return
    _, p, key = c.data.split("_", 2)
    data = _get_data(p)
    cat, fname = _get_cat(p)
    name = data.pop(key, {}).get("name", "?")
    save(fname, data)
    bot.answer_callback_query(c.id)
    bot.send_message(c.from_user.id, f"🗑 «{name}» удалён.")
    edit_menu(c.from_user.id, cat)
 
@bot.callback_query_handler(func=lambda c: c.data.startswith("cn_") or c.data.startswith("cp_"))
def change_field(c):
    if not is_admin(c.from_user.id): return
    bot.answer_callback_query(c.id)
    is_name = c.data.startswith("cn_")
    _, p, key = c.data.split("_", 2)
    data = _get_data(p)
    if key not in data: return
    msg = bot.send_message(c.from_user.id, "Введите новое название:" if is_name else "Введите новую цену:")
    bot.register_next_step_handler(msg, lambda m: apply_change(m, key, p, is_name))
 
def apply_change(m, key, p, is_name):
    if not is_admin(m.chat.id): return
    data = _get_data(p)
    cat, fname = _get_cat(p)
    if key not in data: return
    data[key]["name" if is_name else "price"] = m.text.strip()
    save(fname, data)
    bot.send_message(m.chat.id, "✅ Изменено!")
    edit_menu(m.chat.id, cat)
 
# ── ОБЩИЙ ──
@bot.message_handler(content_types=["text", "photo", "document"])
def relay(m):
    save_user(m.chat.id)
    if m.chat.id in active_chats:
        partner = active_chats[m.chat.id]["partner"]
        prefix = "💬 Продавец: " if is_admin(m.chat.id) else "💬 Покупатель: "
        try:
            if m.text: bot.send_message(partner, prefix + m.text)
            elif m.photo: bot.send_photo(partner, m.photo[-1].file_id, caption=m.caption or "")
            elif m.document: bot.send_document(partner, m.document.file_id, caption=m.caption or "")
        except: pass
        return
    if (m.photo or m.document) and not is_admin(m.chat.id):
        for a in ADMINS: bot.forward_message(a, m.chat.id, m.message_id)
        bot.send_message(m.chat.id, "✅ Доказательство отправлено продавцу.")
 
print("🤖 Бот запущен...")
bot.infinity_polling()