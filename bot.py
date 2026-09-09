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

# Railway Environment Variables se token fetch karega
TOKEN = os.getenv("BOT_TOKEN")

class Game:
    def __init__(self):
        self.is_active = False
        self.players = {}
        self.votes = {}
        self.phase = "LOBBY"

game = Game()

def assign_roles(player_ids):
    ids = list(player_ids)
    random.shuffle(ids)
    roles = ["Mafia", "Detective", "Doctor"] + ["Villager"] * (len(ids) - 3)
    if len(ids) < 3:
        roles = ["Mafia"] + ["Villager"] * (len(ids) - 1)
    return {p_id: roles[i] for i, p_id in enumerate(ids)}

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game.is_active:
        await update.message.reply_text("Ek game pehle se chal raha hai!")
        return
    game.is_active = True
    game.players = {}
    game.votes = {}
    game.phase = "LOBBY"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Join Game", callback_data="join_game")]
    ])
    await update.message.reply_text(
        "🎭 **Mafia Game Lobby Open!**\n\n"
        "Game join karne ke liye niche button par click karein.\n"
        "Jab sab join kar lein, to /play type karein.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    if game.phase != "LOBBY":
        await query.answer("Game already start ho chuka hai!", show_alert=True)
        return
    if user.id in game.players:
        await query.answer("Aap pehle se game me hain!", show_alert=True)
        return
        
    game.players[user.id] = {"name": user.first_name, "role": None, "alive": True}
    await query.answer("Aap game me join ho gaye!")
    await query.message.edit_text(
        f"🎭 **Mafia Game Lobby Open!**\n\n"
        f"Total Players: {len(game.players)}\n"
        f"Players: {', '.join([p['name'] for p in game.players.values()])}\n\n"
        "Niche button se join karein ya host /play start kare.",
        reply_markup=query.message.reply_markup,
        parse_mode="Markdown"
    )

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game.is_active or game.phase != "LOBBY":
        await update.message.reply_text("Pehle /newgame start karein!")
        return
    if len(game.players) < 2:
        await update.message.reply_text("Game start karne ke liye kam se kam 2 players chahiye!")
        return
        
    game.phase = "NIGHT"
    roles = assign_roles(game.players.keys())
    
    for p_id, role in roles.items():
        game.players[p_id]["role"] = role
        try:
            await context.bot.send_message(
                chat_id=p_id,
                text=f"🤫 **Aapka Secret Role Hai:** {role}\n\nGroup chat me apna role reveal mat karna!"
            )
        except Exception:
            await update.message.reply_text(
                f"⚠️ User {game.players[p_id]['name']} ko DM nahi bhej saka. Unhe pehle Bot ko DM me /start karna padega."
            )

    await update.message.reply_text(
        "🤫 **Raat ho gayi hai... Sabhi apna role DM me check karein!**\n\n"
        "Voting phase ke liye 10 seconds ka wait karein...",
        parse_mode="Markdown"
    )
    await asyncio.sleep(10)
    await start_day_voting(update, context)

async def start_day_voting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game.phase = "DAY"
    game.votes = {}
    buttons = [[InlineKeyboardButton(f"Vote {data['name']}", callback_data=f"vote_{p_id}")] 
               for p_id, data in game.players.items() if data["alive"]]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="☀️ **Din ho gaya hai!**\n\nAapko lagta hai Mafia kaun hai? Niche click karke vote karein:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    voter_id = query.from_user.id
    
    if game.phase != "DAY" or voter_id not in game.players or not game.players[voter_id]["alive"]:
        await query.answer("Aap vote nahi kar sakte!", show_alert=True)
        return
        
    target_id = int(query.data.split("_")[1])
    game.votes[voter_id] = target_id
    await query.answer("Aapne vote register kar diya!")
    
    alive_count = sum(1 for p in game.players.values() if p["alive"])
    if len(game.votes) >= alive_count:
        await count_votes(context, query.message.chat_id)

async def count_votes(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    vote_counts = {}
    for target_id in game.votes.values():
        vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
    eliminated_id = max(vote_counts, key=vote_counts.get)
    eliminated_player = game.players[eliminated_id]
    eliminated_player["alive"] = False
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💀 **{eliminated_player['name']}** ko eliminate kar diya gaya! Role: **{eliminated_player['role']}**.",
        parse_mode="Markdown"
    )
    
    mafia_alive = any(p["alive"] for p in game.players.values() if p["role"] == "Mafia")
    villagers_alive = any(p["alive"] for p in game.players.values() if p["role"] != "Mafia")
    
    if not mafia_alive:
        await context.bot.send_message(chat_id=chat_id, text="🎉 **Villagers Jeet Gaye!**")
        game.is_active = False
    elif not villagers_alive:
        await context.bot.send_message(chat_id=chat_id, text="🔴 **Mafia Jeet Gaya!**")
        game.is_active = False

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN variable nahi mila!")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("newgame", start_game))
    app.add_handler(CommandHandler("play", play_game))
    app.add_handler(CallbackQueryHandler(join_callback, pattern="^join_game$"))
    app.add_handler(CallbackQueryHandler(vote_callback, pattern="^vote_"))
    
    print("Bot Start Ho Gaya...")
    app.run_polling()

if __name__ == "__main__":
    main()
