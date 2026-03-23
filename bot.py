import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
TOKEN = os.getenv("8628690709:AAG8geeLA8EiDQV1veAgx8LdOaxxVRKq1N0") # Fetches from Render/Env
DAILY_LIKES = 30

# --- IN-MEMORY DATA ---
profiles = {}      
steps = {}         
likes_count = {}   
user_likes = {}    
matches = {}       
premium_users = set()

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Create Profile 🔎", callback_data="setup")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌸 Hi there! Welcome to MatchBot!\nLet's help you find your perfect partner ❤️",
        reply_markup=reply_markup
    )

# --- HANDLERS ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "setup":
        profiles[user_id] = {"media": []}
        steps[user_id] = "name"
        likes_count[user_id] = DAILY_LIKES
        await query.message.reply_text("First, tell me your **name**:")

    elif data.startswith("gender_"):
        profiles[user_id]["gender"] = data.split("_")[1].capitalize()
        steps[user_id] = "age"
        await query.message.reply_text("How old are you? (Enter a number)")

    elif data.startswith("desc_"):
        desc_map = {
            "desc_fun": "Fun and outgoing 😄",
            "desc_calm": "Calm and thoughtful 🤔",
            "desc_adventure": "Adventurous 🌍",
            "desc_other": "Other"
        }
        profiles[user_id]["description"] = desc_map.get(data, "Unique ✨")
        steps[user_id] = "photo"
        keyboard = [[InlineKeyboardButton("Skip Photos 📷", callback_data="skip_photo")]]
        await query.message.reply_text(
            "Upload up to 3 photos, or skip this step:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "skip_photo":
        await prompt_location(query.message, user_id)

    elif data == "view":
        await show_next_profile(update, user_id)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    step = steps.get(user_id)
    text = update.message.text

    if step == "name":
        profiles[user_id]["name"] = text
        steps[user_id] = "gender"
        keyboard = [[InlineKeyboardButton("Boy 👦", callback_data="gender_boy"),
                     InlineKeyboardButton("Girl 👧", callback_data="gender_girl")]]
        await update.message.reply_text(f"Nice to meet you, {text}! Are you a:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == "age":
        if text.isdigit():
            profiles[user_id]["age"] = text
            steps[user_id] = "description"
            keyboard = [
                [InlineKeyboardButton("Fun 😄", callback_data="desc_fun"), InlineKeyboardButton("Calm 🤔", callback_data="desc_calm")],
                [InlineKeyboardButton("Adventurous 🌍", callback_data="desc_adventure")]
            ]
            await update.message.reply_text("Pick a vibe:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("Please enter age as a number (e.g., 25).")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if steps.get(user_id) == "photo":
        file_id = update.message.photo[-1].file_id
        profiles[user_id]["media"].append(file_id)
        
        count = len(profiles[user_id]["media"])
        if count < 3:
            keyboard = [[InlineKeyboardButton("Finish & Send Location 📍", callback_data="skip_photo")]]
            await update.message.reply_text(f"Saved {count}/3. Send more or finish:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await prompt_location(update.message, user_id)

async def prompt_location(message, user_id):
    steps[user_id] = "location"
    keyboard = [[KeyboardButton("Send my location 📍", request_location=True)]]
    await message.reply_text("Almost done! Please share your location:", 
                             reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    loc = update.message.location
    profiles[user_id]["location"] = (loc.latitude, loc.longitude)
    steps[user_id] = "done"

    preview = f"✅ Profile Created!\nName: {profiles[user_id]['name']}\nAge: {profiles[user_id]['age']}"
    keyboard = [[InlineKeyboardButton("View Profiles", callback_data="view")]]
    
    await update.message.reply_text(preview, reply_markup=ReplyKeyboardRemove()) # Remove big location button
    await update.message.reply_text("Ready to find a match?", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_next_profile(update: Update, user_id):
    for other_id, profile in profiles.items():
        if other_id != user_id and other_id not in user_likes.get(user_id, set()):
            keyboard = [[InlineKeyboardButton("Like ❤️", callback_data=f"like_{other_id}"),
                         InlineKeyboardButton("Dislike ❌", callback_data=f"dislike_{other_id}")]]
            caption = f"{profile['name']}, {profile['age']}\n{profile.get('description', '')}"
            
            if profile.get("media"):
                await update.effective_message.reply_photo(profile["media"][0], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.effective_message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard))
            return
    await update.effective_message.reply_text("No one new nearby! Check back later.")

async def handle_matching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    action, target_id = query.data.split("_")
    target_id = int(target_id)

    if action == "like":
        if user_id not in user_likes: user_likes[user_id] = set()
        user_likes[user_id].add(target_id)

        if target_id in user_likes and user_id in user_likes[target_id]:
            await query.message.reply_text(f"It's a Match! 🎉 with {profiles[target_id]['name']}")
            await context.bot.send_message(target_id, f"It's a Match! 🎉 with {profiles[user_id]['name']}")

    await show_next_profile(update, user_id)

# --- MAIN ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(setup|gender_|desc_|skip_photo|view)$"))
    app.add_handler(CallbackQueryHandler(handle_matching, pattern="^(like|dislike)_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))

    print("🚀 Bot is running...")
    app.run_polling()
