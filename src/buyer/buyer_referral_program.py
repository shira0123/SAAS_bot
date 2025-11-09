import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

WALLET_METHOD, WALLET_DETAILS = range(2)

async def show_buyer_referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    referral_link = f"https://t.me/{context.bot.username}?start=buyref_{user_data['referral_code']}"
    
    keyboard = [
        [KeyboardButton("📊 My Referrals"), KeyboardButton("💵 Referral Earnings")],
        [KeyboardButton("💳 Set Wallet Info"), KeyboardButton("💸 Withdraw Earnings")],
        [KeyboardButton("🔙 Back to Buyer Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    commission_rate = db.get_saas_referral_commission_rate() * 100
    
    message = f"""
🎁 **Buyer Referral Program**

💰 **Referral Balance:** ${user_data.get('buyer_referral_balance', 0):.2f}
📊 **Commission Rate:** {commission_rate:.1f}%

**Your Referral Link:**
`{referral_link}`

**How it works:**
1. Share your referral link
2. When someone buys a plan using your link, you earn {commission_rate:.1f}% commission
3. Withdraw your earnings anytime

Use the menu below to manage your referrals:
"""
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_my_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    earnings = db.get_buyer_referral_earnings(user.id, limit=10)
    
    if not earnings:
        await update.message.reply_text(
            "📊 **My Referrals**\n\n"
            "You haven't earned any referral commissions yet.\n"
            "Share your referral link to start earning!"
        )
        return
    
    message = "📊 **My Referral Earnings**\n\n"
    total = 0
    
    for earning in earnings:
        username = earning.get('referred_username', 'Unknown')
        plan_type = earning.get('plan_type', 'N/A')
        commission = float(earning['commission_amount'])
        date = earning['created_at'].strftime('%Y-%m-%d')
        total += commission
        
        message += f"• **@{username}** - {plan_type}\n"
        message += f"  💵 ${commission:.2f} on {date}\n\n"
    
    message += f"**Total Earned:** ${total:.2f}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def start_wallet_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 PayPal", callback_data="wallet_paypal")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="wallet_bank")],
        [InlineKeyboardButton("💰 Crypto", callback_data="wallet_crypto")],
        [InlineKeyboardButton("❌ Cancel", callback_data="wallet_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💳 **Set Wallet Info**\n\n"
        "Choose your preferred payment method for withdrawals:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return WALLET_METHOD

async def receive_wallet_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "wallet_cancel":
        await query.edit_message_text("❌ Wallet setup cancelled.")
        return ConversationHandler.END
    
    method_map = {
        "wallet_paypal": "PayPal",
        "wallet_bank": "Bank Transfer",
        "wallet_crypto": "Crypto"
    }
    
    context.user_data['wallet_method'] = method_map.get(query.data, "PayPal")
    
    await query.edit_message_text(
        f"💳 **Payment Method:** {context.user_data['wallet_method']}\n\n"
        f"Please provide your payment details:\n"
        f"(e.g., PayPal email, bank account, wallet address)\n\n"
        f"Send /cancel to abort."
    )
    
    return WALLET_DETAILS

async def receive_wallet_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    details = update.message.text
    
    cursor = db.connection.cursor()
    cursor.execute("""
        UPDATE users
        SET buyer_wallet_method = %s,
            buyer_wallet_details = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (context.user_data['wallet_method'], details, user.id))
    cursor.close()
    
    await update.message.reply_text(
        f"✅ **Wallet Info Updated!**\n\n"
        f"**Method:** {context.user_data['wallet_method']}\n"
        f"**Details:** {details}\n\n"
        f"You can now withdraw your referral earnings."
    )
    
    return ConversationHandler.END

async def cancel_wallet_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Wallet setup cancelled.")
    return ConversationHandler.END

def get_buyer_referral_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 Set Wallet Info$"), start_wallet_setup)],
        states={
            WALLET_METHOD: [CallbackQueryHandler(receive_wallet_method)],
            WALLET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_wallet_details)]
        },
        fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_wallet_setup)]
    )
