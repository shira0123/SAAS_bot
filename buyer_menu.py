import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from database import Database

logger = logging.getLogger(__name__)

db = Database()

def get_buyer_menu():
    keyboard = [
        [KeyboardButton("💎 Buy Plan")],
        [KeyboardButton("💰 Deposit"), KeyboardButton("📋 My Plans")],
        [KeyboardButton("📊 Plan History"), KeyboardButton("🎁 Referral Program")],
        [KeyboardButton("👔 Reseller Panel"), KeyboardButton("💬 Support")],
        [KeyboardButton("🔙 Back to Seller Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def show_buyer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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
    rates = db.get_saas_rates()
    
    message = """
💎 **Buy Engagement Plan**

We offer 4 types of engagement services:

"""
    
    for rate in rates:
        if rate['rate_type'] == 'per_view':
            message += f"📊 **Per View:** ${rate['price_per_unit']:.4f}/view\n"
        elif rate['rate_type'] == 'per_day_view':
            message += f"📅 **Daily Views:** ${rate['price_per_unit']:.2f}/view/day\n"
        elif rate['rate_type'] == 'per_reaction':
            message += f"❤️ **Per Reaction:** ${rate['price_per_unit']:.4f}/reaction\n"
        elif rate['rate_type'] == 'per_day_reaction':
            message += f"📅 **Daily Reactions:** ${rate['price_per_unit']:.2f}/reaction/day\n"
    
    message += """

**How it works:**
1. Choose your plan type
2. Specify your channel and requirements
3. Pay from your buyer wallet
4. We deliver engagement automatically!

📝 To create a custom plan, please contact support or use the web dashboard (coming soon).
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
💰 **Deposit Funds**

Add money to your buyer wallet to purchase engagement plans.

**Payment Methods:**
• Cryptocurrency (USDT, BTC, ETH)
• PayPal
• Bank Transfer
• Other methods available

**How to deposit:**
1. Contact admin with your deposit amount
2. You'll receive payment instructions
3. Send payment and provide transaction ID
4. Funds added to your wallet within 1-24 hours

💬 Contact support to initiate a deposit.
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

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
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    message = f"""
🎁 **Buyer Referral Program**

Invite other buyers and earn commission on their purchases!

**Your Referral Link:**
`t.me/{context.bot.username}?start=buyer_{user_data['referral_code']}`

**Commission Rate:** 5% of all purchases
**Your Earnings:** ${user_data['referral_earnings']:.2f}

**How it works:**
1. Share your referral link with potential buyers
2. When they sign up and make purchases
3. You earn 5% commission automatically!

💡 The more buyers you refer, the more passive income you earn!
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def reseller_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not db.is_reseller(user.id):
        message = """
👔 **Reseller Panel**

You are not currently a reseller.

**Become a Reseller:**
Resellers can purchase plans at wholesale prices and resell to their own clients with a custom margin.

**Benefits:**
• Higher profit margins (10-30%)
• Bulk discount rates
• White-label options
• Priority support
• Custom payment terms

💬 Contact support to apply for reseller status.
"""
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    reseller_info = db.get_reseller_info(user.id)
    
    message = f"""
👔 **Reseller Dashboard**

📊 **Your Stats:**
• Margin: {reseller_info['margin_percentage']:.1f}%
• Total Sales: ${reseller_info['total_sales']:.2f}
• Total Profit: ${reseller_info['total_profit']:.2f}
• Status: {'Active' if reseller_info['is_active'] else 'Inactive'}

**Reseller Features:**
• Purchase at wholesale prices
• Add your own margin
• Manage client orders
• Track sales and profits

💬 Contact support for reseller assistance.
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def switch_to_seller_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot import get_seller_menu
    
    await update.message.reply_text(
        "🔙 Switched to Seller Menu",
        reply_markup=get_seller_menu()
    )
