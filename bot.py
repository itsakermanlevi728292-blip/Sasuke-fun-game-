import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

# Media Link (Photo/GIF URL)
START_MEDIA_URL = "https://telegra.ph/file/0b1062972eb2e8612140a.jpg"

class MafiaGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.is_active = False
        self.chat_id = None
        self.phase = "LOBBY"  # LOBBY, NIGHT, DAY
        self.players = {}     # {user_id: {"name": str, "role": str, "alive": bool}}
        self.night_actions = {"mafia_target": None, "doctor_target": None}
        self.day_votes = {}   # {voter_id: target_id}

game = MafiaGame()

# --- HELPER FUNCTIONS ---
def distribute_roles(player_ids):
    ids = list(player_ids)
    random.shuffle(ids)
    count = len(ids)
    
    roles = ["Mafia"]
    if count >= 3:
        roles.append("Detective")
    if count >= 4:
        roles.append("Doctor")
    if count >= 5:
        roles.append("Mafia")
        
    while len(roles) < count:
        roles.append("Villager")
        
    random.shuffle(roles)
    return {p_id: roles[i] for i, p_id in enumerate(ids)}

def get_alive_players():
    return {p_id: data for p_id, data in game.players.items() if data["alive"]}

# --- COMMAND HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Custom Mafia Game Bot Welcome Message with Photo & Quote Block."""
    user_name = update.effective_user.first_name

    # Premium Emoji Tags
    E_AVATAR = '<tg-emoji emoji-id="6274076470671319190">👩‍🦰</tg-emoji>'
    E_ARROW  = '<tg-emoji emoji-id="6269180384047533905">⏩</tg-emoji>'
    E_LIGHT  = '<tg-emoji emoji-id="6269267069372469947">⚡</tg-emoji>'
    E_SPARK  = '<tg-emoji emoji-id="6269085886177087845">✨</tg-emoji>'
    E_POWER  = '<tg-emoji emoji-id="5474322494657699248">👑</tg-emoji>'

    welcome_text = (
        f"<blockquote>"
        f"{E_AVATAR} <b>ʜєʏ {user_name}</b> {E_AVATAR}\n\n"
        f"{E_ARROW} <b>ᴡєʟᴄσϻє ᴛσ ᴍᴀғɪᴀ ɢᴀᴍᴇ ʙᴏᴛ 🎭˼{E_SPARK}</b>\n"
        f"<b>ᴘʀєϻɪᴜϻ | ᴀᴅ-ғʀєє | ᴜʟᴛʀᴧ ꜱϻσσᴛʜ</b>\n\n"
        f"{E_ARROW} <b>ʜɪɢʜ-ǫᴜᴧʟɪᴛʏ ɢᴧϻє ʜσꜱᴛ ʙσᴛ</b>\n"
        f"<b>ғσʀ ᴛєʟᴇɢʀᴧϻ ɢʀσᴜᴘꜱ & ᴄʜᴧηηєʟꜱ</b>\n\n"
        f"{E_LIGHT} <b>ꜱєᴄʀєᴛ ʀσ🇱є ᴧꜱꜱɪɢηϻєηᴛ</b>\n"
        f"{E_LIGHT} <b>ᴧᴜᴛσϻᴧᴛєᴅ ɴɪɢʜᴛ/ᴅᴧʏ ᴘʜᴧꜱєꜱ</b>\n"
        f"{E_LIGHT} <b>ɪηᴛєʀᴧᴄᴛɪᴠє ᴠσᴛɪηɢ | ησ ʟᴧɢ</b>\n\n"
        f"{E_ARROW} <b>ᴛᴧ🇵 ʜєʟᴘ ғσʀ ᴄσϻϻᴧηᴅꜱ</b>\n\n"
        f"{E_POWER} <b>ᴘσᴡєʀєᴅ ʙʏ : <a href='https://t.me/sasuke_qt'>𝛅 ᥲ s 𝛖 𝛋 ᴇ ࿐</a></b>\n"
        f"── ⋅ ⋅ ────── ⋅᯽⋅ ────── ⋅ ⋅ ──"
        f"</blockquote>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ ➕ ADD ME TO YOUR CHAT ➕ ✨", url=f"https://t.me/{context.bot.username}?startgroup=true", style="primary")],
        [
            InlineKeyboardButton("TOP ⚡ UPDATES ↗️", url="https://t.me/ll_ABOUT_SASUKE_ll", style="success"),
            InlineKeyboardButton("💬 SUPPORT ↗️", url="https://t.me/+W3WrSwmHeaY5NjM9", style="danger")
        ],
        [InlineKeyboardButton("🎮 HELP AND COMMANDS 🎮", callback_data="show_help", style="success")],
        [InlineKeyboardButton("👑 OWNER ↗️", url="https://t.me/sasuke_qt", style="danger")]
    ])

    await update.message.reply_photo(
        photo=START_MEDIA_URL,
        caption=welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📖 <b>Mafia Game Rules & Roles</b>\n\n"
        "🎭 <b>Game Roles:</b>\n"
        "• 🔴 <b>Mafia:</b> Eliminate villagers secretly without getting exposed.\n"
        "• 🩺 <b>Doctor:</b> Choose one player each night to save from attack.\n"
        "• 🕵️ <b>Detective:</b> Investigate one player each night to check if they are Mafia.\n"
        "• 🟢 <b>Villagers:</b> Work together during discussion and vote out the Mafia.\n\n"
        "⚙️ <b>Commands:</b>\n"
        "• <code>/newgame</code> - Open a new game lobby in a group\n"
        "• <code>/play</code> - Start the game match\n"
        "• <code>/cancelgame</code> - Cancel the running game session"
    )
    await update.message.reply_text(rules_text, parse_mode="HTML")

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Please run <code>/newgame</code> inside a Telegram group chat!", parse_mode="HTML")
        return

    if game.is_active:
        await update.message.reply_text("⚠️ A game session is already in progress!")
        return

    game.reset()
    game.is_active = True
    game.chat_id = update.effective_chat.id

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Join Game", callback_data="join_lobby")]])
    await update.message.reply_text(
        "🎭 <b>Mafia Game Lobby Open!</b>\n\n"
        "Click the button below to join the game.\n"
        "Minimum 3 players required. Type <code>/play</code> when ready to begin!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game.is_active:
        await update.message.reply_text("No active game to cancel.")
        return
    game.reset()
    await update.message.reply_text("🛑 <b>Game session has been cancelled.</b>", parse_mode="HTML")

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game.is_active or game.phase != "LOBBY":
        await update.message.reply_text("No active lobby! Start one using <code>/newgame</code>.", parse_mode="HTML")
        return

    if len(game.players) < 3:
        await update.message.reply_text("⚠️ Need at least 3 players to start the game!")
        return

    roles = distribute_roles(game.players.keys())
    for p_id, role in roles.items():
        game.players[p_id]["role"] = role

    await update.message.reply_text("🤫 <b>Roles distributed! Night Phase has begun. Check your DMs!</b>", parse_mode="HTML")
    await start_night_phase(context)

# --- GAME ENGINE LOGIC ---
async def start_night_phase(context: ContextTypes.DEFAULT_TYPE):
    game.phase = "NIGHT"
    game.night_actions = {"mafia_target": None, "doctor_target": None}
    
    alive_players = get_alive_players()
    
    for p_id, data in alive_players.items():
        role = data["role"]
        targets = [
            [InlineKeyboardButton(target["name"], callback_data=f"night_{role}_{t_id}")]
            for t_id, target in alive_players.items()
            if not (role == "Doctor" and t_id == p_id)
        ]
        
        try:
            if role == "Mafia":
                await context.bot.send_message(
                    p_id, "🔴 <b>Night Phase:</b> Select a player to eliminate:",
                    reply_markup=InlineKeyboardMarkup(targets),
                    parse_mode="HTML"
                )
            elif role == "Doctor":
                await context.bot.send_message(
                    p_id, "🩺 <b>Night Phase:</b> Select a player to protect/heal:",
                    reply_markup=InlineKeyboardMarkup(targets),
                    parse_mode="HTML"
                )
            elif role == "Detective":
                await context.bot.send_message(
                    p_id, "🕵️ <b>Night Phase:</b> Select a player to investigate:",
                    reply_markup=InlineKeyboardMarkup(targets),
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_message(p_id, "😴 <b>Night Phase:</b> You are a Villager. Go to sleep...", parse_mode="HTML")
        except Exception:
            pass

    await asyncio.sleep(30)
    await resolve_night(context)

async def resolve_night(context: ContextTypes.DEFAULT_TYPE):
    target_id = game.night_actions["mafia_target"]
    doctor_id = game.night_actions["doctor_target"]
    
    killed_player = None
    if target_id and target_id != doctor_id:
        killed_player = game.players[target_id]
        killed_player["alive"] = False

    night_summary = "☀️ <b>Daytime Has Arrived!</b>\n\n"
    if killed_player:
        night_summary += f"💀 <b>{killed_player['name']}</b> was eliminated during the night!\nTheir secret role was: <b>{killed_player['role']}</b>"
    else:
        night_summary += "🎉 It was a peaceful night! Nobody was killed."

    await context.bot.send_message(game.chat_id, night_summary, parse_mode="HTML")

    if await check_win_conditions(context):
        return

    await start_day_phase(context)

async def start_day_phase(context: ContextTypes.DEFAULT_TYPE):
    game.phase = "DAY"
    game.day_votes = {}
    
    alive_players = get_alive_players()
    buttons = [
        [InlineKeyboardButton(f"Vote {data['name']}", callback_data=f"vote_{p_id}")]
        for p_id, data in alive_players.items()
    ]

    await context.bot.send_message(
        game.chat_id,
        "🗣 <b>Discussion & Voting Time!</b>\nVote for who you suspect is Mafia. You have 45 seconds!",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

    await asyncio.sleep(45)
    await resolve_day(context)

async def resolve_day(context: ContextTypes.DEFAULT_TYPE):
    if game.phase != "DAY":
        return

    if not game.day_votes:
        await context.bot.send_message(game.chat_id, "⌛ Voting time ended with no votes cast. Nobody was eliminated.")
    else:
        vote_counts = {}
        for target_id in game.day_votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
        eliminated_id = max(vote_counts, key=vote_counts.get)
        eliminated_player = game.players[eliminated_id]
        eliminated_player["alive"] = False

        await context.bot.send_message(
            game.chat_id,
            f"💀 <b>{eliminated_player['name']}</b> was voted out!\nTheir secret role was: <b>{eliminated_player['role']}</b>",
            parse_mode="HTML"
        )

    if await check_win_conditions(context):
        return

    await start_night_phase(context)

async def check_win_conditions(context: ContextTypes.DEFAULT_TYPE) -> bool:
    alive = get_alive_players()
    mafia_count = sum(1 for p in alive.values() if p["role"] == "Mafia")
    town_count = len(alive) - mafia_count

    if mafia_count == 0:
        await context.bot.send_message(game.chat_id, "🎉 <b>THE VILLAGERS WIN!</b> All Mafia members have been eliminated.", parse_mode="HTML")
        game.reset()
        return True
    elif mafia_count >= town_count:
        await context.bot.send_message(game.chat_id, "🔴 <b>THE MAFIA WINS!</b> They have overtaken the town.", parse_mode="HTML")
        game.reset()
        return True

    return False

# --- CALLBACK HANDLERS ---
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data == "join_lobby":
        if game.phase != "LOBBY":
            await query.answer("Lobby is closed!", show_alert=True)
            return
        if user.id in game.players:
            await query.answer("Already joined!", show_alert=True)
            return
            
        game.players[user.id] = {"name": user.first_name, "role": None, "alive": True}
        await query.answer("Joined game!")
        
        plist = ", ".join([p["name"] for p in game.players.values()])
        await query.message.edit_text(
            f"🎭 <b>Mafia Game Lobby Open!</b>\n\n"
            f"<b>Total Players:</b> {len(game.players)}\n"
            f"<b>Joined:</b> {plist}\n\n"
            "Host can start with <code>/play</code> when ready.",
            reply_markup=query.message.reply_markup,
            parse_mode="HTML"
        )

    elif data == "show_help":
        help_text = (
            "📖 <b>Help & Commands List</b>\n\n"
            "• <code>/start</code> - Start bot and view welcome screen\n"
            "• <code>/rules</code> - Read role descriptions and game rules\n"
            "• <code>/newgame</code> - Create a new game lobby in a group\n"
            "• <code>/play</code> - Start game match\n"
            "• <code>/cancelgame</code> - Force stop current game"
        )
        await query.message.reply_text(help_text, parse_mode="HTML")
        await query.answer()

    elif data.startswith("night_"):
        _, role, target_id = data.split("_")
        target_id = int(target_id)
        
        if role == "Mafia":
            game.night_actions["mafia_target"] = target_id
            await query.answer("Target locked in.")
            await query.edit_message_text(f"🎯 Target set to: <b>{game.players[target_id]['name']}</b>", parse_mode="HTML")
            
        elif role == "Doctor":
            game.night_actions["doctor_target"] = target_id
            await query.answer("Protection target set.")
            await query.edit_message_text(f"🩺 Protection set on: <b>{game.players[target_id]['name']}</b>", parse_mode="HTML")
            
        elif role == "Detective":
            target = game.players[target_id]
            is_mafia = "YES (Mafia 🔴)" if target["role"] == "Mafia" else "NO (Innocent 🟢)"
            await query.answer()
            await query.edit_message_text(f"🕵️ Inspection Result:\n<b>{target['name']}</b> is Mafia: <b>{is_mafia}</b>", parse_mode="HTML")

    elif data.startswith("vote_"):
        if game.phase != "DAY" or user.id not in get_alive_players():
            await query.answer("You cannot vote right now!", show_alert=True)
            return
            
        target_id = int(data.split("_")[1])
        game.day_votes[user.id] = target_id
        await query.answer("Your vote has been registered!")

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("newgame", new_game))
    app.add_handler(CommandHandler("cancelgame", cancel_game))
    app.add_handler(CommandHandler("play", play_game))
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    print("Bot Engine Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
