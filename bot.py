from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from datetime import datetime, timedelta

# ----------------------------
# BotFather token
# ----------------------------
TOKEN = "8628690709:AAHltDWRucF-c1bOXPR6fv9ZQ2YxAVB_KMk"

# ----------------------------
# In-memory storage (replace later with a database)
# ----------------------------
profiles = {}        # {user_id: profile_info}
steps = {}           # {user_id: current_step}
likes_count = {}     # {user_id: remaining_likes}
user_likes = {}      # {user_id: set(liked_user_ids)}
matches = {}         # {user_id: set(matched_user_ids)}
premium_users = set()  # {user_id}

# Constants
DAILY_LIKES = 30

# ----------------------------
# /start command
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
        # initialize daily likes
        if user_id not in premium_users:
            likes_count[user_id] = DAILY_LIKES
        return

    # ----------------------------
    # Gender selection
    # ----------------------------
    if query.data.startswith("gender_"):
        profiles[user_id]["gender"] = query.data.split("_")[1].capitalize()
        steps[user_id] = "age"
        await query.message.reply_text("Enter your age:")
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
    # Viewing nearby profiles
    # ----------------------------
    if query.data == "view":
        await show_next_profile(update, context, user_id)
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
    if "media" in profile and profile["media"]:
        await update.message.reply_photo(profile["media"][0], caption=preview_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(preview_text, reply_markup=reply_markup)

# ----------------------------
# Show next nearby profile
# ----------------------------
async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    # For simplicity: pick first profile not self, not already liked
    for other_id, profile in profiles.items():
        if other_id == user_id:
            continue
        if user_id in user_likes and other_id in user_likes[user_id]:
            continue
        # Show profile
        keyboard = [
            [
                InlineKeyboardButton("Like ❤️", callback_data=f"like_{other_id}"),
                InlineKeyboardButton("Dislike ❌", callback_data=f"dislike_{other_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"{profile.get('name','')} - {profile.get('age','')} yrs\n{profile.get('description','')}"
        if "media" in profile and profile["media"]:
            await update.callback_query.message.reply_photo(profile["media"][0], caption=text, reply_markup=reply_markup)
        else:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
        return
    await update.callback_query.message.reply_text("No more profiles nearby!")

# ----------------------------
# Handle Like/Dislike actions
# ----------------------------
async def handle_like_dislike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("like_") or query.data.startswith("dislike_"):
        target_id = int(query.data.split("_")[1])

        if query.data.startswith("like_"):
            # Check daily limit
            if user_id not in premium_users and likes_count.get(user_id, DAILY_LIKES) <= 0:
                await query.message.reply_text("You used all your likes today! Buy premium or wait for tomorrow.")
                return
            # Deduct like
            if user_id not in premium_users:
                likes_count[user_id] -= 1

            # Save like
            if user_id not in user_likes:
                user_likes[user_id] = set()
            user_likes[user_id].add(target_id)

            # Check match
            if target_id in user_likes and user_id in user_likes[target_id]:
                # Match found
                if user_id not in matches:
                    matches[user_id] = set()
                if target_id not in matches:
                    matches[target_id] = set()
                matches[user_id].add(target_id)
                matches[target_id].add(user_id)

                await query.message.reply_text(f"Hurray! You matched with {profiles[target_id]['name']} 🎉")
                try:
                    await context.bot.send_message(target_id, f"Hurray! You matched with {profiles[user_id]['name']} 🎉")
                except:
                    pass
        # Dislike does nothing special
        await show_next_profile(update, context, user_id)

# ----------------------------
# Telegram bot setup
# ----------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(CallbackQueryHandler(handle_like_dislike, pattern="^(like|dislike)_"))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.LOCATION, handle_location))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🚀 Starting bot...")
app.run_polling()
