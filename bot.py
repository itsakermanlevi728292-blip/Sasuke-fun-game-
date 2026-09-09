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
    """Handles /start command instantly without failing on external links."""
    user_name = update.effective_user.first_name
    text = (
        f"👋 **Welcome to Mafia Host, {user_name}!**\n\n"
        "I am a fully automated Mafia/Werewolf game engine built for Telegram groups.\n\n"
        "📌 **How to Play:**\n"
        "1. Add me to a Telegram Group and give me Admin rights.\n"
        "2. Type `/newgame` in the group to start a lobby.\n"
        "3. Ensure all players press `/start` here in DM so I can assign secret roles!\n\n"
        "Use `/rules` for complete role instructions."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📖 **Mafia Game Rules**\n\n"
        "🎭 **Roles:**\n"
        "• 🔴 **Mafia:** Cooperate to eliminate town members without revealing yourselves.\n"
        "• 🩺 **Doctor:** Select a player each night to save from potential elimination.\n"
        "• 🕵️ **Detective:** Investigate one player each night to learn their true identity.\n"
        "• 🟢 **Villagers:** Deduce who the Mafia members are and vote them out during the day.\n\n"
        "⚙️ **Commands:**\n"
        "• `/newgame` - Open game lobby\n"
        "• `/play` - Start match\n"
        "• `/cancelgame` - Abort active session"
    )
    await update.message.reply_text(rules_text, parse_mode="Markdown")

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Please run `/newgame` inside a Telegram group chat!")
        return

    if game.is_active:
        await update.message.reply_text("⚠️ A game session is already in progress!")
        return

    game.reset()
    game.is_active = True
    game.chat_id = update.effective_chat.id

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Join Game", callback_data="join_lobby")]])
    await update.message.reply_text(
        "🎭 **Mafia Game Lobby Open!**\n\n"
        "Click below to join the match.\n"
        "Require minimum 3 players to start. Type `/play` when ready.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game.is_active:
        await update.message.reply_text("No active game to cancel.")
        return
    game.reset()
    await update.message.reply_text("🛑 **Game session has been cancelled.**")

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game.is_active or game.phase != "LOBBY":
        await update.message.reply_text("No active lobby! Start one using `/newgame`.")
        return

    if len(game.players) < 3:
        await update.message.reply_text("⚠️ Need at least 3 players to start the game!")
        return

    roles = distribute_roles(game.players.keys())
    for p_id, role in roles.items():
        game.players[p_id]["role"] = role

    await update.message.reply_text("🤫 **Roles distributed! Starting Night 1... Check your DMs!**")
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
                    p_id, "🔴 **Night Phase:** Select a target to eliminate:",
                    reply_markup=InlineKeyboardMarkup(targets)
                )
            elif role == "Doctor":
                await context.bot.send_message(
                    p_id, "🩺 **Night Phase:** Select a player to protect/heal:",
                    reply_markup=InlineKeyboardMarkup(targets)
                )
            elif role == "Detective":
                await context.bot.send_message(
                    p_id, "🕵️ **Night Phase:** Select a player to investigate:",
                    reply_markup=InlineKeyboardMarkup(targets)
                )
            else:
                await context.bot.send_message(p_id, "😴 **Night Phase:** You are a Villager. Go to sleep...")
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

    night_summary = "☀️ **Daytime Arrives!**\n\n"
    if killed_player:
        night_summary += f"💀 **{killed_player['name']}** was eliminated during the night!\nRole: **{killed_player['role']}**"
    else:
        night_summary += "🎉 It was a peaceful night! Nobody was killed."

    await context.bot.send_message(game.chat_id, night_summary, parse_mode="Markdown")

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
        "🗣 **Discussion & Voting Time!**\nVote for who you suspect is Mafia. You have 45 seconds!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await asyncio.sleep(45)
    await resolve_day(context)

async def resolve_day(context: ContextTypes.DEFAULT_TYPE):
    if game.phase != "DAY":
        return

    if not game.day_votes:
        await context.bot.send_message(game.chat_id, "⌛ Voting time ended with no cast votes. Nobody was eliminated.")
    else:
        vote_counts = {}
        for target_id in game.day_votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
        eliminated_id = max(vote_counts, key=vote_counts.get)
        eliminated_player = game.players[eliminated_id]
        eliminated_player["alive"] = False

        await context.bot.send_message(
            game.chat_id,
            f"💀 **{eliminated_player['name']}** was voted out!\nRole: **{eliminated_player['role']}**",
            parse_mode="Markdown"
        )

    if await check_win_conditions(context):
        return

    await start_night_phase(context)

async def check_win_conditions(context: ContextTypes.DEFAULT_TYPE) -> bool:
    alive = get_alive_players()
    mafia_count = sum(1 for p in alive.values() if p["role"] == "Mafia")
    town_count = len(alive) - mafia_count

    if mafia_count == 0:
        await context.bot.send_message(game.chat_id, "🎉 **THE VILLAGERS WIN!** All Mafia members have been eliminated.")
        game.reset()
        return True
    elif mafia_count >= town_count:
        await context.bot.send_message(game.chat_id, "🔴 **THE MAFIA WINS!** They have overtaken the village.")
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
            f"🎭 **Mafia Game Lobby Open!**\n\n"
            f"**Total Players:** {len(game.players)}\n"
            f"**Joined:** {plist}\n\n"
            "Host can start with `/play` when ready.",
            reply_markup=query.message.reply_markup,
            parse_mode="Markdown"
        )

    elif data.startswith("night_"):
        _, role, target_id = data.split("_")
        target_id = int(target_id)
        
        if role == "Mafia":
            game.night_actions["mafia_target"] = target_id
            await query.answer("Target locked in.")
            await query.edit_message_text(f"🎯 Target set to: {game.players[target_id]['name']}")
            
        elif role == "Doctor":
            game.night_actions["doctor_target"] = target_id
            await query.answer("Protection target set.")
            await query.edit_message_text(f"🩺 Protect set on: {game.players[target_id]['name']}")
            
        elif role == "Detective":
            target = game.players[target_id]
            is_mafia = "YES (Mafia 🔴)" if target["role"] == "Mafia" else "NO (Innocent 🟢)"
            await query.answer()
            await query.edit_message_text(f"🕵️ Inspection Result:\n**{target['name']}** is Mafia: **{is_mafia}**", parse_mode="Markdown")

    elif data.startswith("vote_"):
        if game.phase != "DAY" or user.id not in get_alive_players():
            await query.answer("You cannot vote!", show_alert=True)
            return
            
        target_id = int(data.split("_")[1])
        game.day_votes[user.id] = target_id
        await query.answer("Vote registered!")

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
            
