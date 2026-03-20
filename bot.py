print("🔄 Force rebuild for Render...", flush=True)from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# ----------------------------
# Bot token
# ----------------------------
TOKEN = "8628690709:AAGXwmwnN7T4ejFjRWV-yM7R-LrAuOvhFBc"

# ----------------------------
# Storage for profiles and steps (in-memory)
# ----------------------------
profiles = {}
steps = {}

# ----------------------------
# /start command
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start 🔎", callback_data="setup")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌸 Hello! Welcome to your new dating adventure! 🌸\n\n"
        "Press Start to create your profile and meet new friends! 💖",
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
        await query.message.reply_text("✨ First, enter your **name**:", reply_markup=ReplyKeyboardRemove())
        return

    # ----------------------------
    # Gender selection
    # ----------------------------
    if query.data.startswith("gender_"):
        gender_map = {
            "gender_boy": "Boy",
            "gender_girl": "Girl"
        }
        profiles[user_id]["gender"] = gender_map[query.data]
        steps[user_id] = "age"

        keyboard = [
            [InlineKeyboardButton("18-25", callback_data="age_18_25")],
            [InlineKeyboardButton("26-35", callback_data="age_26_35")],
            [InlineKeyboardButton("36-45", callback_data="age_36_45")],
            [InlineKeyboardButton("46+", callback_data="age_46")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Select your age range:", reply_markup=reply_markup)
        return

    # ----------------------------
    # Age selection
    # ----------------------------
    if query.data.startswith("age_"):
        age_map = {
            "age_18_25": "18-25",
            "age_26_35": "26-35",
            "age_36_45": "36-45",
            "age_46": "46+"
        }
        profiles[user_id]["age"] = age_map[query.data]
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

        # Ask for photo with skip button
        keyboard = [[InlineKeyboardButton("Skip ⏭️", callback_data="skip_photo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Great! Now send your profile photo (optional, up to 4). Or skip:", reply_markup=reply_markup)
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
# Handle text messages (name & description)
# ----------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id in steps:
        step = steps[user_id]

        if step == "name":
            profiles[user_id]["name"] = text
            steps[user_id] = "gender"

            keyboard = [
                [InlineKeyboardButton("Boy 👦", callback_data="gender_boy")],
                [InlineKeyboardButton("Girl 👧", callback_data="gender_girl")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Are you a Boy or Girl?", reply_markup=reply_markup)

# ----------------------------
# Handle photos
# ----------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in steps and steps[user_id] == "photo":
        photo_file = await update.message.photo[-1].get_file()
        file_id = photo_file.file_id

        if "photos" not in profiles[user_id]:
            profiles[user_id]["photos"] = []

        profiles[user_id]["photos"].append(file_id)

        if len(profiles[user_id]["photos"]) < 4:
            await update.message.reply_text(f"Photo added! You can send {4 - len(profiles[user_id]['photos'])} more or press skip ⏭️.")
        else:
            steps[user_id] = "location"
            keyboard = [[KeyboardButton("Send my location 📍", request_location=True)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Almost done! Please share your location:", reply_markup=reply_markup)

# ----------------------------
# Handle location
# ----------------------------
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in steps and steps[user_id] == "location":
        loc = update.message.location
        profiles[user_id]["location"] = (loc.latitude, loc.longitude)
        steps[user_id] = "done"

        profile = profiles[user_id]
        keyboard = [
            [InlineKeyboardButton("View Nearby Profiles", callback_data="view")],
            [InlineKeyboardButton("Edit My Profile", callback_data="edit")],
            [InlineKeyboardButton("Buy Premium ✨", callback_data="premium")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        preview_text = f"""
Profile Preview 👤

Name: {profile.get('name', '')}
Gender: {profile.get('gender', '')}
Age: {profile.get('age', '')}
About: {profile.get('description', '')}
Location: {profile['location'][0]}, {profile['location'][1]}
"""
        if "photos" in profile:
            await update.message.reply_photo(profile["photos"][0], caption=preview_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(preview_text, reply_markup=reply_markup)

# ----------------------------
# Telegram app setup
# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.LOCATION, handle_location))

# ----------------------------
# Run bot
# ----------------------------
print("🚀 Starting bot...")  # Force log for Render
app.run_polling()
print("❌ Bot stopped!")
