import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from src.database.database import Database
import src.seller.seller_profile as seller_profile
import src.seller.seller_withdrawals as seller_withdrawals
import src.admin.admin_controls as admin_controls
import src.admin.admin_reporting as admin_reporting
from src.seller.account_seller import get_account_sell_handler

# --- NEW: Import Seller Bot Token ---
from src.database.config import SELLER_BOT_TOKEN, ADMIN_IDS, MIN_WITHDRAWAL

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

def generate_referral_code(length=8):
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_seller_menu():
    """Returns the ReplyKeyboardMarkup for the seller menu."""
    keyboard = [
        [KeyboardButton("💰 Sell TG Account")],
        [KeyboardButton("💸 Withdraw"), KeyboardButton("👤 Profile")],
        [KeyboardButton("🎁 Refer & Earn"), KeyboardButton("💬 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    """Returns the ReplyKeyboardMarkup for the admin menu."""
    keyboard = [
        [KeyboardButton("📊 Statistics"), KeyboardButton("👥 Users")],
        [KeyboardButton("💳 Withdrawals"), KeyboardButton("📱 Accounts")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("🔙 Back to User Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command for the seller bot."""
    user = update.effective_user
    existing_user = db.get_user(user.id)
    
    if not existing_user:
        referral_code = generate_referral_code()
        while db.get_user_by_referral(referral_code):
            referral_code = generate_referral_code()
        
        referred_by = None
        if context.args and len(context.args) > 0:
            ref_code = context.args[0]
            # Check for both seller and buyer referral codes
            if ref_code.startswith('buyref_'):
                ref_code = ref_code.replace('buyref_', '')
                
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

Choose an option from the menu below:
"""
        if is_admin:
            welcome_message += "\n🔑 **Admin Access Granted** (Seller Bot)"
    
    is_admin = db.is_admin(user.id)
    menu = get_admin_menu() if is_admin else get_seller_menu()
    
    await update.message.reply_text(welcome_message, reply_markup=menu)

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Refer & Earn' button."""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    referral_count = db.get_referral_count(user.id)
    
    message = f"""
🎁 **Refer & Earn (Seller Program)**

Invite your friends to sell their accounts and earn commission!

**Your Seller Referral Link:**
`t.me/{context.bot.username}?start={user_data['referral_code']}`

**Your Stats:**
• Total Referrals: {referral_count}
• Referral Earnings: ${user_data['referral_earnings']:.2f}

**How it works:**
1. Share your referral link
2. When someone signs up using your link and sells an account
3. You earn a percentage of their account sale!
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Support' button."""
    message = """
💬 **Support**

Need help? We're here for you!

**Common Questions:**
• How long does verification take? Usually instant!
• When will I receive payment? After successful account verification
• How do withdrawals work? Request via the Withdraw button

**Contact Admin:**
For any issues, questions, or concerns, please contact our support team.

**Business Hours:**
Monday - Sunday: 9 AM - 11 PM (UTC)

We typically respond within a few hours!
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /setprice <amount>"""
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
    """Handles text messages and buttons from the seller menu."""
    text = update.message.text
    
    if text == "👤 Profile":
        await seller_profile.show_profile(update, context)
    elif text == "🎁 Refer & Earn":
        await handle_referral(update, context)
    elif text == "💬 Support":
        await handle_support(update, context)
    elif text == "🔙 Back to Menu":
        await update.message.reply_text(
            "📱 Main Menu",
            reply_markup=get_seller_menu()
        )
    elif text == "🔙 Back to User Menu":
        if db.is_admin(update.effective_user.id):
            await update.message.reply_text("Switching to user menu...", reply_markup=get_seller_menu())
    # --- Admin Menu Handling ---
    elif db.is_admin(update.effective_user.id):
        if text == "📊 Statistics":
            await admin_reporting.stats_command(update, context)
        elif text == "👥 Users":
            await admin_reporting.alluser_command(update, context)
        elif text == "💳 Withdrawals":
            await admin_controls.list_pending_withdrawals(update, context)
        elif text == "📱 Accounts":
            await context.bot.send_message(update.effective_chat.id, "Please use the /accounts command.")
        elif text == "⚙️ Settings":
            await context.bot.send_message(update.effective_chat.id, "Admin settings are command-based (e.g., /setprice, /setref, /withdrawlimit).")
        else:
            await update.message.reply_text("Please use the menu buttons below to navigate.")
    else:
        await update.message.reply_text("Please use the menu buttons below to navigate.")


def main():
    """Starts the Seller Bot."""
    try:
        db.init_schema()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    if not SELLER_BOT_TOKEN:
        logger.error("SELLER_BOT_TOKEN not found in environment variables!")
        return
    
    application = Application.builder().token(SELLER_BOT_TOKEN).build()
    
    # --- Conversation Handlers ---
    payout_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 Set Payout Info$"), seller_profile.start_set_payout)],
        states={
            seller_profile.PAYOUT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_profile.receive_payout_method)],
            seller_profile.PAYOUT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_profile.receive_payout_details)],
        },
        fallbacks=[CommandHandler("cancel", seller_profile.cancel_payout_setup)],
    )
    
    withdraw_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), seller_withdrawals.start_withdraw)],
        states={
            seller_withdrawals.REQUEST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_withdrawals.receive_amount)],
        },
        fallbacks=[CommandHandler("cancel", seller_withdrawals.cancel_withdraw)],
    )
    
    application.add_handler(get_account_sell_handler())
    application.add_handler(payout_handler)
    application.add_handler(withdraw_handler)

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setprice", setprice))
    
    # Seller Admin Reporting
    application.add_handler(CommandHandler("setref", admin_reporting.setref_command))
    application.add_handler(CommandHandler("accsell", admin_reporting.accsell_command))
    application.add_handler(CommandHandler("alluser", admin_reporting.alluser_command))
    application.add_handler(CommandHandler("stats", admin_reporting.stats_command))
    
    # Seller Admin Controls
    application.add_handler(CommandHandler("withdraws", admin_controls.list_pending_withdrawals))
    application.add_handler(CommandHandler("withdrawlimit", admin_controls.set_withdrawal_limits))
    application.add_handler(CommandHandler("ban", admin_controls.ban_user_command))
    application.add_handler(CommandHandler("unban", admin_controls.unban_user_command))
    application.add_handler(CommandHandler("stopwithdraw", admin_controls.stop_withdraw_command))
    application.add_handler(CommandHandler("allowwithdraw", admin_controls.allow_withdraw_command))

    # Callback Handlers for admin controls
    application.add_handler(CallbackQueryHandler(admin_controls.view_withdrawal_detail, pattern="^withdrawal_view_"))
    application.add_handler(CallbackQueryHandler(admin_controls.approve_withdrawal, pattern="^withdrawal_approve_"))
    application.add_handler(CallbackQueryHandler(admin_controls.reject_withdrawal, pattern="^withdrawal_reject_"))
    application.add_handler(CallbackQueryHandler(admin_controls.back_to_withdrawal_list, pattern="^withdrawal_back$"))

    # --- Message Handler ---
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Seller Bot (Bot 1) started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()