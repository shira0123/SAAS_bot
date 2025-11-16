import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

def get_buyer_menu():
    """
    Returns the ReplyKeyboardMarkup for the buyer menu.
    The "Back to Seller Menu" button is removed.
    """
    keyboard = [
        [KeyboardButton("💎 Buy Plan")],
        [KeyboardButton("💰 Deposit"), KeyboardButton("📋 My Plans")],
        [KeyboardButton("📊 Plan History"), KeyboardButton("🎁 Referral Program")],
        [KeyboardButton("👔 Reseller Panel"), KeyboardButton("💬 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def show_buyer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the main buyer menu."""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        # This case might happen if a user starts the buyer bot
        # without ever starting the seller bot.
        # We should create them.
        from main_buyer import generate_referral_code
        referral_code = generate_referral_code()
        while db.get_user_by_referral(referral_code):
            referral_code = generate_referral_code()
            
        db.create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referral_code=referral_code,
            referred_by=None # No referral context here
        )
        user_data = db.get_user(user.id)

    is_reseller = db.is_reseller(user.id)
    
    welcome_message = f"""
💎 **Buyer Menu**

👋 Welcome, {user.first_name}!

💳 **Buyer Wallet:** ${user_data['buyer_wallet_balance']:.2f}
"""
    
    if is_reseller:
        reseller_info = db.get_reseller_info(user.id)
        welcome_message += f"""
👔 **Reseller Status:** Active
📈 **Your Margin:** {reseller_info['margin_percentage']:.1f}%
💵 **Total Profit:** ${reseller_info['total_profit']:.2f}
"""
    
    welcome_message += """

Choose an option below to get started:

💎 **Buy Plan** - Purchase engagement services
💰 **Deposit** - Add funds to your wallet
📋 **My Plans** - View active plans
📊 **Plan History** - See past orders
🎁 **Referral Program** - Earn from referrals
👔 **Reseller Panel** - Manage reseller account
"""
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_buyer_menu(),
        parse_mode='Markdown'
    )

async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.buyer.buy_plan import show_plan_types
    await show_plan_types(update, context)

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.buyer.deposit_menu import show_deposit_methods
    await show_deposit_methods(update, context)

async def my_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    orders = db.get_user_orders(user.id, limit=5)
    
    if not orders:
        await update.message.reply_text(
            "📋 **My Plans**\n\n"
            "You don't have any active plans yet.\n\n"
            "Use 💎 Buy Plan to get started!"
        )
        return
    
    message = "📋 **My Active Plans**\n\n"
    
    for order in orders:
        if order['status'] == 'active':
            progress = (order['delivered_posts'] / order['total_posts']) * 100 if order['total_posts'] > 0 else 0
            message += f"**Plan #{order['id']}**\n"
            message += f"• Channel: @{order['channel_username']}\n"
            message += f"• Type: {order['plan_type']}\n"
            message += f"• Views: {order['views_per_post']} per post\n"
            message += f"• Progress: {order['delivered_posts']}/{order['total_posts']} ({progress:.1f}%)\n"
            message += f"• Status: {order['status'].capitalize()}\n\n"
    
    if len(message) == len("📋 **My Active Plans**\n\n"):
        message += "No active plans found.\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def plan_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    orders = db.get_user_orders(user.id, limit=10)
    
    if not orders:
        await update.message.reply_text(
            "📊 **Plan History**\n\n"
            "No orders found."
        )
        return
    
    message = "📊 **Plan History**\n\n"
    
    for order in orders:
        message += f"**Order #{order['id']}** - {order['created_at'].strftime('%Y-%m-%d')}\n"
        message += f"• Channel: @{order['channel_username']}\n"
        message += f"• Views: {order['views_per_post']} × {order['total_posts']} posts\n"
        message += f"• Price: ${order['price']:.2f}\n"
        message += f"• Status: {order['status'].capitalize()}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def buyer_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.buyer.buyer_referral_program import show_buyer_referral_menu
    await show_buyer_referral_menu(update, context)

async def reseller_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from src.buyer.reseller_panel import show_reseller_panel
    await show_reseller_panel(update, context)

# --- REMOVED ---
# The switch_to_seller_menu function is no longer needed.