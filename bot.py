import sqlite3
from datetime import datetime, date
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ----------------------------
# Replace with your BotFather token
# ----------------------------
TOKEN = "8628690709:AAGXwmwnN7T4ejFjRWV-yM7R-LrAuOvhFBc"

# Optional: Provider token for payments (set up later)
PROVIDER_TOKEN = "YOUR_PAYMENT_PROVIDER_TOKEN"

# ----------------------------
# SQLite setup
# ----------------------------
conn = sqlite3.connect("bot_database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    city TEXT,
    latitude REAL,
    longitude REAL,
    description TEXT,
    media_ids TEXT,
    premium INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    like_reset TEXT,
    referral_code TEXT,
    likes_credits INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS likes (
    liker_id INTEGER,
    liked_id INTEGER,
    PRIMARY KEY (liker_id, liked_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    user1_id INTEGER,
    user2_id INTEGER,
    matched_at TEXT,
    confirmed1 INTEGER DEFAULT 0,
    confirmed2 INTEGER DEFAULT 0,
    PRIMARY KEY (user1_id, user2_id)
)
""")
conn.commit()

# ----------------------------
# Steps tracker
# ----------------------------
steps = {}

# ----------------------------
# Helper functions
# ----------------------------
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def save_user_field(user_id, field, value):
    if get_user(user_id):
        cursor.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    else:
        cursor.execute(f"INSERT INTO users (user_id, {field}) VALUES (?, ?)", (user_id, value))
    conn.commit()

def generate_referral(user_id):
    return f"REF{user_id}"

def reset_likes(user):
    today = str(date.today())
    if not user[10] or user[10] != today:
        cursor.execute("UPDATE users SET like_count=0, like_reset=? WHERE user_id=?", (today, user[0]))
        conn.commit()

# ----------------------------
# /start command
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not get_user(user_id):
        save_user_field(user_id, "referral_code", generate_referral(user_id))
    steps[user_id] = "name"
    await update.message.reply_text(
        "👋 Hi there! Let’s set up your profile so you can find awesome matches 💖\n\n"
        "First, tell me your Name:"
    )

# ----------------------------
# Handle text input
# ----------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if steps.get(user_id) == "name":
        save_user_field(user_id, "name", text)
        steps[user_id] = "age"
        await update.message.reply_text("Enter your Age:")
        return

    if steps.get(user_id) == "age":
        if not text.isdigit() or int(text) < 18 or int(text) > 99:
            await update.message.reply_text("Please enter a valid age between 18 and 99:")
            return
        save_user_field(user_id, "age", int(text))
        steps[user_id] = "location"
        keyboard = [[KeyboardButton("Send Current Location 📍")]]
        await update.message.reply_text(
            "Type your city or send your location:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return

    if steps.get(user_id) == "location":
        save_user_field(user_id, "city", text)
        steps[user_id] = "description"
        await update.message.reply_text("Enter a short description about yourself:")
        return

    if steps.get(user_id) == "description":
        save_user_field(user_id, "description", text)
        steps[user_id] = "media"
        keyboard = [[KeyboardButton("Skip ⏭")]]
        await update.message.reply_text(
            "Send up to 4 photos/videos of yourself (optional) or press Skip ⏭",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return

    if steps.get(user_id) == "media" and text == "Skip ⏭":
        steps[user_id] = None
        await show_main_menu(update, user_id)
        return

# ----------------------------
# Handle location
# ----------------------------
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    loc = update.message.location
    if steps.get(user_id) == "location":
        save_user_field(user_id, "latitude", loc.latitude)
        save_user_field(user_id, "longitude", loc.longitude)
        steps[user_id] = "description"
        await update.message.reply_text("Enter a short description about yourself:")

# ----------------------------
# Handle media uploads
# ----------------------------
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if steps.get(user_id) != "media":
        return

    media_ids = []
    if update.message.photo:
        for photo in update.message.photo[-4:]:
            media_ids.append(photo.file_id)
    if update.message.video:
        media_ids.append(update.message.video.file_id)

    existing = get_user(user_id)[7] or ""
    if existing:
        media_ids = existing.split(",") + media_ids
    media_ids = media_ids[:4]  # max 4
    save_user_field(user_id, "media_ids", ",".join(media_ids))

    steps[user_id] = None
    await show_main_menu(update, user_id)

# ----------------------------
# Main menu
# ----------------------------
async def show_main_menu(update, user_id):
    keyboard = [
        [InlineKeyboardButton("View Nearby Profiles", callback_data="show_profiles")],
        [InlineKeyboardButton("Edit My Profile", callback_data="setup")],
        [InlineKeyboardButton("Buy Premium ✨", callback_data="premium")],
        [InlineKeyboardButton("Invite Friends", callback_data="invite")]
    ]
    if update.message:
        await update.message.reply_text("Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.message.reply_text("Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------------------
# Button handler (Like, Dislike, Match)
# ----------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "setup":
        steps[user_id] = "name"
        await query.message.reply_text("Editing profile. Enter your Name:")
        return

    if data == "show_profiles":
        await show_next_profile(update, user_id)
        return

    if data == "premium":
        save_user_field(user_id, "premium", 1)
        await query.message.reply_text("✨ You are now a Premium user! ✨")
        return

    if data == "invite":
        user = get_user(user_id)
        await query.message.reply_text(f"Share this code with friends to earn +5 likes each: {user[11]}")

    if data.startswith("like_"):
        liked_id = int(data.split("_")[1])
        await handle_like(update, user_id, liked_id, context)

    if data.startswith("dislike_") or data.startswith("snooze_"):
        await show_next_profile(update, user_id)

    if data.startswith("showmatch_") or data.startswith("notinterested_"):
        await handle_match_response(update, user_id, data, context)

# ----------------------------
# Show next profile
# ----------------------------
async def show_next_profile(update, user_id):
    user = get_user(user_id)
    reset_likes(user)

    cursor.execute("SELECT * FROM users WHERE user_id != ? LIMIT 1", (user_id,))
    profile = cursor.fetchone()
    if not profile:
        await update.callback_query.message.reply_text("No profiles available right now.")
        return

    media_ids = profile[7].split(",") if profile[7] else []
    media_group = []
    for m in media_ids:
        media_group.append(InputMediaPhoto(m))

    text = f"Name: {profile[1]}\nAge: {profile[2]}\nAbout: {profile[6]}"
    keyboard = [
        [InlineKeyboardButton("Like ❤️", callback_data=f"like_{profile[0]}"),
         InlineKeyboardButton("Dislike ❌", callback_data=f"dislike_{profile[0]}")],
        [InlineKeyboardButton("Snooze ⏰", callback_data=f"snooze_{profile[0]}")]
    ]
    if user[8]:
        keyboard[1].append(InlineKeyboardButton("Send Message ✉️", callback_data=f"message_{profile[0]}"))

    if media_group:
        await update.callback_query.message.reply_media_group(media_group)
    await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------------------
# Handle Likes
# ----------------------------
async def handle_like(update, liker_id, liked_id, context):
    user = get_user(liker_id)
    reset_likes(user)
    daily_limit = 30
    total_likes = user[9] + user[12]
    if not user[8] and total_likes >= daily_limit:
        await update.callback_query.message.reply_text("You reached your daily like limit. Upgrade to Premium for unlimited likes!")
        return

    cursor.execute("INSERT OR IGNORE INTO likes (liker_id, liked_id) VALUES (?, ?)", (liker_id, liked_id))
    if not user[8]:
        cursor.execute("UPDATE users SET like_count = like_count + 1 WHERE user_id=?", (liker_id,))
    conn.commit()

    cursor.execute("SELECT * FROM likes WHERE liker_id=? AND liked_id=?", (liked_id, liker_id))
    if cursor.fetchone():
        cursor.execute("INSERT OR IGNORE INTO matches (user1_id, user2_id, matched_at) VALUES (?, ?, ?)",
                       (min(liker_id, liked_id), max(liker_id, liked_id), str(datetime.now())))
        conn.commit()
        keyboard = [
            [InlineKeyboardButton("Show ✅", callback_data=f"showmatch_{liked_id}"),
             InlineKeyboardButton("Not Interested ❌", callback_data=f"notinterested_{liked_id}")]
        ]
        await update.callback_query.message.reply_text("🎉 You have a new match! What do you want to do?", reply_markup=InlineKeyboardMarkup(keyboard))
        try:
            await context.bot.send_message(liked_id, "🎉 Someone liked you! What do you want to do?", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Show ✅", callback_data=f"showmatch_{liker_id}"),
                  InlineKeyboardButton("Not Interested ❌", callback_data=f"notinterested_{liker_id}")]]
            ))
        except:
            pass

    await show_next_profile(update, liker_id)

# ----------------------------
# Handle match responses
# ----------------------------
async def handle_match_response(update, user_id, data, context):
    query = update.callback_query
    await query.answer()

    action, match_user_id = data.split("_")
    match_user_id = int(match_user_id)

    user1 = min(user_id, match_user_id)
    user2 = max(user_id, match_user_id)

    match = cursor.execute("SELECT * FROM matches WHERE user1_id=? AND user2_id=?", (user1, user2)).fetchone()
    if not match:
        await query.message.reply_text("Match not found or already resolved.")
        return

    if user_id == user1:
        if action == "showmatch":
            cursor.execute("UPDATE matches SET confirmed1=1 WHERE user1_id=? AND user2_id=?", (user1, user2))
        else:
            cursor.execute("DELETE FROM matches WHERE user1_id=? AND user2_id=?", (user1, user2))
            conn.commit()
            await query.message.reply_text("You declined the match.")
            return
    else:
        if action == "showmatch":
            cursor.execute("UPDATE matches SET confirmed2=1 WHERE user1_id=? AND user2_id=?", (user1, user2))
        else:
            cursor.execute("DELETE FROM matches WHERE user1_id=? AND user2_id=?", (user1, user2))
            conn.commit()
            await query.message.reply_text("You declined the match.")
            return

    conn.commit()
    match = cursor.execute("SELECT confirmed1, confirmed2 FROM matches WHERE user1_id=? AND user2_id=?", (user1, user2)).fetchone()
    if match and match[0] == 1 and match[1] == 1:
        user1_obj = await context.bot.get_chat(user1)
        user2_obj = await context.bot.get_chat(user2)

        msg1 = f"🎉 Hurray! You and {user2_obj.username or user2_obj.first_name} like each other!\nHave fun chatting! 💌"
        msg2 = f"🎉 Hurray! You and {user1_obj.username or user1_obj.first_name} like each other!\nHave fun chatting! 💌"

        await context.bot.send_message(user1, msg1)
        await context.bot.send_message(user2, msg2)

        cursor.execute("DELETE FROM matches WHERE user1_id=? AND user2_id=?", (user1, user2))
        conn.commit()

# ----------------------------
# Telegram app setup
# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.LOCATION, handle_location))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
app.add_handler(CallbackQueryHandler(button))

# ----------------------------
# Run bot
# ----------------------------
app.run_polling()
