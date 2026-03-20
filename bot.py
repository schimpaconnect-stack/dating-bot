from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ----------------------------
# BotFather token
# ----------------------------
TOKEN = "8628690709:AAHltDWRucF-c1bOXPR6fv9ZQ2YxAVB_KMk"

# ----------------------------
# In-memory storage (can later be replaced by a database)
# ----------------------------
profiles = {}  # stores user profile info
steps = {}     # stores user current step
likes_count = {}  # daily likes counter
premium_users = set()  # example premium user set

# ----------------------------
# Start command
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start 🔎", callback_data="setup")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌸 Hi there! Welcome to MatchBot!\nLet's help you find your perfect partner ❤️",
        reply_markup=reply_markup
    )

# ----------------------------
# Inline button handler
# ----------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # ----------------------------
    # Start setup
    # ----------------------------
    if query.data == "setup":
        profiles[user_id] = {}
        steps[user_id] = "name"
        await query.message.reply_text("First, tell me your **name**:")
        return

    # ----------------------------
    # Handle gender selection
    # ----------------------------
    if query.data.startswith("gender_"):
        profiles[user_id]["gender"] = query.data.split("_")[1].capitalize()
        steps[user_id] = "age"
        await query.message.reply_text("Enter your age:")
        return

    # ----------------------------
    # Age selection (exact number)
    # ----------------------------
    if steps.get(user_id) == "age" and query.data.startswith("age_"):
        profiles[user_id]["age"] = query.data.split("_")[1]
        steps[user_id] = "description"
        keyboard = [
            [InlineKeyboardButton("Fun and outgoing 😄", callback_data="desc_fun")],
            [InlineKeyboardButton("Calm and thoughtful 🤔", callback_data="desc_calm")],
            [InlineKeyboardButton("Adventurous 🌍", callback_data="desc_adventure")],
            [InlineKeyboardButton("Other ✏️", callback_data="desc_other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Choose a short description about yourself:", reply_markup=reply_markup)
        return

    # ----------------------------
    # Description selection
    # ----------------------------
    if query.data.startswith("desc_"):
        desc_map = {
            "desc_fun": "Fun and outgoing 😄",
            "desc_calm": "Calm and thoughtful 🤔",
            "desc_adventure": "Adventurous 🌍",
            "desc_other": "Other"
        }
        profiles[user_id]["description"] = desc_map[query.data]
        steps[user_id] = "photo"
        keyboard = [[InlineKeyboardButton("Skip 📷", callback_data="skip_photo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Great! You can now send up to 3 photos/videos (optional). Or skip this step:",
            reply_markup=reply_markup
        )
        return

    # ----------------------------
    # Skip photo
    # ----------------------------
    if query.data == "skip_photo":
        steps[user_id] = "location"
        keyboard = [[KeyboardButton("Send my location 📍", request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await query.message.reply_text("Almost done! Please share your location:", reply_markup=reply_markup)
        return

# ----------------------------
# Handle text messages (name, messages)
# ----------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if steps.get(user_id) == "name":
        profiles[user_id]["name"] = text
        steps[user_id] = "gender"
        keyboard = [
            [InlineKeyboardButton("Boy 👦", callback_data="gender_boy")],
            [InlineKeyboardButton("Girl 👧", callback_data="gender_girl")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Are you a Boy or Girl?", reply_markup=reply_markup)
        return

# ----------------------------
# Handle photo messages
# ----------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if steps.get(user_id) == "photo":
        if "media" not in profiles[user_id]:
            profiles[user_id]["media"] = []
        # Limit 3 files
        if len(profiles[user_id]["media"]) < 3:
            file_id = update.message.photo[-1].file_id
            profiles[user_id]["media"].append(file_id)
            await update.message.reply_text(f"Photo saved ({len(profiles[user_id]['media'])}/3). Send more or click Skip.")
        if len(profiles[user_id]["media"]) == 3:
            steps[user_id] = "location"
            keyboard = [[KeyboardButton("Send my location 📍", request_location=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Almost done! Please share your location:", reply_markup=reply_markup)

# ----------------------------
# Handle location
# ----------------------------
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    loc = update.message.location
    profiles[user_id]["location"] = (loc.latitude, loc.longitude)
    steps[user_id] = "done"

    profile = profiles[user_id]
    keyboard = [
        [InlineKeyboardButton("View Nearby Profiles", callback_data="view")],
        [InlineKeyboardButton("Edit Profile", callback_data="edit")],
        [InlineKeyboardButton("Buy Premium ✨", callback_data="premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    preview_text = f"""
👤 Profile Preview
Name: {profile['name']}
Gender: {profile.get('gender', '-') }
Age: {profile.get('age', '-') }
About: {profile.get('description', '-') }
Location: {profile['location'][0]}, {profile['location'][1]}
"""
    # Send first photo if exists
    if "media" in profile and profile["media"]:
        await update.message.reply_photo(profile["media"][0], caption=preview_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(preview_text, reply_markup=reply_markup)

# ----------------------------
# Telegram bot setup
# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.LOCATION, handle_location))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🚀 Starting bot...")
app.run_polling()
