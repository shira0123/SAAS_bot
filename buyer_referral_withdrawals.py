import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from database import Database

logger = logging.getLogger(__name__)

db = Database()

REQUEST_AMOUNT = range(1)

MIN_WITHDRAWAL = 5.00

async def start_withdraw_referral_earnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    balance = float(user_data.get('buyer_referral_balance', 0))
    
    if not user_data.get('buyer_wallet_method'):
        await update.message.reply_text(
            "❌ **Wallet Not Set**\n\n"
            "Please set your wallet info first using the '💳 Set Wallet Info' button."
        )
        return ConversationHandler.END
    
    if balance < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ **Insufficient Balance**\n\n"
            f"Minimum withdrawal: ${MIN_WITHDRAWAL:.2f}\n"
            f"Your balance: ${balance:.2f}\n\n"
            f"Keep referring to reach the minimum!"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"💸 **Withdraw Referral Earnings**\n\n"
        f"💰 **Available Balance:** ${balance:.2f}\n"
        f"💳 **Payment Method:** {user_data.get('buyer_wallet_method', 'Not set')}\n\n"
        f"📝 **Enter withdrawal amount:**\n"
        f"(Min: ${MIN_WITHDRAWAL:.2f}, Max: ${balance:.2f})\n\n"
        f"Send /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return REQUEST_AMOUNT

async def receive_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number."
        )
        return REQUEST_AMOUNT
    
    balance = float(user_data.get('buyer_referral_balance', 0))
    
    if amount < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ Amount must be at least ${MIN_WITHDRAWAL:.2f}"
        )
        return REQUEST_AMOUNT
    
    if amount > balance:
        await update.message.reply_text(
            f"❌ Amount exceeds your balance (${balance:.2f})"
        )
        return REQUEST_AMOUNT
    
    withdrawal = db.create_buyer_referral_withdrawal(
        user.id,
        amount,
        user_data.get('buyer_wallet_method'),
        user_data.get('buyer_wallet_details')
    )
    
    if withdrawal:
        await update.message.reply_text(
            f"✅ **Withdrawal Request Submitted!**\n\n"
            f"**Amount:** ${amount:.2f}\n"
            f"**Method:** {user_data.get('buyer_wallet_method')}\n"
            f"**Request ID:** #{withdrawal['id']}\n\n"
            f"Your request is pending admin approval.\n"
            f"You'll be notified once it's processed."
        )
    else:
        await update.message.reply_text(
            "❌ Failed to create withdrawal request. Please try again."
        )
    
    return ConversationHandler.END

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Withdrawal cancelled.")
    return ConversationHandler.END

def get_buyer_referral_withdrawal_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw Earnings$"), start_withdraw_referral_earnings)],
        states={
            REQUEST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdrawal_amount)]
        },
        fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_withdraw)]
    )
