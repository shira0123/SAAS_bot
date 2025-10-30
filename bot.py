import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from database import Database
from config import BOT_TOKEN, MIN_WITHDRAWAL
import random
import string

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_seller_menu():
    keyboard = [
        [KeyboardButton("💰 Sell TG Account")],
        [KeyboardButton("💸 Withdraw"), KeyboardButton("👤 Profile")],
        [KeyboardButton("🎁 Refer & Earn"), KeyboardButton("💬 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    keyboard = [
        [KeyboardButton("📊 Statistics"), KeyboardButton("👥 Users")],
        [KeyboardButton("💳 Withdrawals"), KeyboardButton("📱 Accounts")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("🔙 Back to User Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    existing_user = db.get_user(user.id)
    
    if not existing_user:
        referral_code = generate_referral_code()
        while db.get_user_by_referral(referral_code):
            referral_code = generate_referral_code()
        
        referred_by = None
        if context.args and len(context.args) > 0:
            ref_code = context.args[0]
            referrer = db.get_user_by_referral(ref_code)
            if referrer:
                referred_by = referrer['user_id']
        
        db.create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referral_code=referral_code,
            referred_by=referred_by
        )
        
        account_price = db.get_account_price()
        welcome_message = f"""
🎉 Welcome to the Account Marketplace Bot!

👋 Hello {user.first_name}!

You can earn money by selling your Telegram accounts to our platform.

💰 **Current Rate:** ${account_price:.2f} per account
💸 **Minimum Withdrawal:** ${MIN_WITHDRAWAL}
🎁 **Referral Bonus:** Earn commission for every friend you invite!

Choose an option from the menu below to get started:
"""
    else:
        is_admin = db.is_admin(user.id)
        welcome_message = f"""
👋 Welcome back, {user.first_name}!

💰 **Seller Balance:** ${existing_user['seller_balance']:.2f}
💳 **Buyer Balance:** ${existing_user['buyer_wallet_balance']:.2f}

Choose an option from the menu below:
"""
        if is_admin:
            welcome_message += "\n🔑 **Admin Access Granted**"
    
    is_admin = db.is_admin(user.id)
    menu = get_admin_menu() if is_admin else get_seller_menu()
    
    await update.message.reply_text(welcome_message, reply_markup=menu)

async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if not user_data['can_withdraw']:
        await update.message.reply_text("❌ Withdrawals are currently disabled for your account.")
        return
    
    balance = float(user_data['seller_balance'])
    
    message = f"""
💸 **Withdrawal**

**Available Balance:** ${balance:.2f}
**Minimum Withdrawal:** ${MIN_WITHDRAWAL}

To request a withdrawal, type:
/withdraw <amount> <method> <details>

**Example:**
/withdraw 10 PayPal myemail@example.com

**Supported Methods:**
• PayPal
• Bank Transfer
• Crypto (USDT)
• Wise

Your withdrawal will be processed by an admin within 24-48 hours.
"""
    await update.message.reply_text(message)

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    accounts_sold = db.get_user_accounts_count(user.id)
    total_earned = db.get_user_total_earnings(user.id)
    
    message = f"""
👤 **Your Profile**

**User ID:** `{user.id}`
**Username:** @{user.username or 'Not set'}
**Name:** {user.first_name} {user.last_name or ''}

**💰 Balances:**
• Seller Balance: ${user_data['seller_balance']:.2f}
• Buyer Balance: ${user_data['buyer_wallet_balance']:.2f}

**📊 Statistics:**
• Accounts Sold: {accounts_sold}
• Total Earned: ${total_earned:.2f}
• Referral Earnings: ${user_data['referral_earnings']:.2f}

**🎁 Referral Code:** `{user_data['referral_code']}`
• Share: t.me/{context.bot.username}?start={user_data['referral_code']}

**Status:** {'✅ Active' if not user_data['is_banned'] else '❌ Banned'}
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    referral_count = db.get_referral_count(user.id)
    
    message = f"""
🎁 **Refer & Earn**

Invite your friends and earn commission on their earnings!

**Your Referral Link:**
`t.me/{context.bot.username}?start={user_data['referral_code']}`

**Your Stats:**
• Total Referrals: {referral_count}
• Referral Earnings: ${user_data['referral_earnings']:.2f}

**How it works:**
1. Share your referral link
2. When someone signs up using your link
3. You earn a percentage of their account sales!

💡 The more people you refer, the more you earn!
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
💬 **Support**

Need help? We're here for you!

**Common Questions:**
• How long does verification take? Usually instant!
• When will I receive payment? After successful account verification
• How do withdrawals work? Request via /withdraw, we process within 24-48h

**Contact Admin:**
For any issues, questions, or concerns:
• Use /admin command to send a message to our team
• Or contact @YourSupportUsername

**Business Hours:**
Monday - Sunday: 9 AM - 11 PM (UTC)

We typically respond within a few hours!
"""
    await update.message.reply_text(message)

async def setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    if not context.args or len(context.args) != 1:
        current_price = db.get_account_price()
        await update.message.reply_text(
            f"💰 **Current Account Price:** ${current_price:.2f}\n\n"
            "**Usage:** /setprice <amount>\n"
            "**Example:** /setprice 15.00",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_price = float(context.args[0])
        if new_price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0")
            return
        
        db.set_account_price(new_price)
        await update.message.reply_text(
            f"✅ **Account Price Updated!**\n\n"
            f"New price: ${new_price:.2f} per account\n\n"
            "This will apply to all new account sales.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid price format. Please use a number (e.g., 15.00)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💸 Withdraw":
        await handle_withdraw(update, context)
    elif text == "👤 Profile":
        await handle_profile(update, context)
    elif text == "🎁 Refer & Earn":
        await handle_referral(update, context)
    elif text == "💬 Support":
        await handle_support(update, context)
    elif text == "🔙 Back to User Menu":
        if db.is_admin(update.effective_user.id):
            await update.message.reply_text("Switching to user menu...", reply_markup=get_seller_menu())
    else:
        is_admin = db.is_admin(update.effective_user.id)
        if is_admin and text in ["📊 Statistics", "👥 Users", "💳 Withdrawals", "📱 Accounts", "⚙️ Settings"]:
            await update.message.reply_text(f"Admin feature '{text}' - Coming soon in future phases!")
        else:
            await update.message.reply_text("Please use the menu buttons below to navigate.")

def main():
    try:
        db.init_schema()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    from account_seller import get_account_sell_handler
    
    application.add_handler(get_account_sell_handler())
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setprice", setprice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
