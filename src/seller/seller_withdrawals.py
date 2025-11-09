import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from src.database.database import Database
from src.database.config import ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

REQUEST_AMOUNT = 0

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        user = db.get_user(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not found. Please /start again.")
            return ConversationHandler.END
        
        if user['is_banned']:
            await update.message.reply_text(
                "🚫 **Account Suspended**\n\n"
                "Your account has been suspended. You cannot request withdrawals.\n"
                "Please contact support for more information.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        if not user['can_withdraw']:
            await update.message.reply_text(
                "🚫 **Withdrawals Disabled**\n\n"
                "Withdrawals have been disabled for your account.\n"
                "Please contact support for more information.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        stats = db.get_user_stats(user_id)
        balance = float(stats['seller_balance'])
        
        if not stats['payout_method'] or not stats['payout_details']:
            await update.message.reply_text(
                "⚠️ **Payout Information Required**\n\n"
                "Before you can withdraw, you need to set up your payout information.\n\n"
                "Please go to 👤 Profile and use the '💳 Set Payout Info' button.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        withdrawal_count = db.get_user_withdrawal_count(user_id)
        limits = db.get_withdrawal_limits()
        
        if withdrawal_count < len(limits):
            min_withdrawal = limits[withdrawal_count]
        else:
            min_withdrawal = limits[-1]
        
        context.user_data['min_withdrawal'] = min_withdrawal
        context.user_data['user_balance'] = balance
        
        withdrawal_number = withdrawal_count + 1
        
        await update.message.reply_text(
            f"💸 **Withdrawal Request**\n\n"
            f"💰 Your Balance: ${balance:.2f}\n"
            f"📊 This is your #{withdrawal_number} withdrawal\n"
            f"💵 Minimum Amount: ${min_withdrawal:.2f}\n\n"
            f"Please enter the amount you want to withdraw (in USD):",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("❌ Cancel")]
            ], resize_keyboard=True),
            parse_mode='Markdown'
        )
        
        return REQUEST_AMOUNT
        
    except Exception as e:
        logger.error(f"Error starting withdrawal: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again."
        )
        return ConversationHandler.END

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "❌ Cancel":
        await update.message.reply_text(
            "❌ Withdrawal cancelled.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
                [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
                [KeyboardButton("💬 Support")]
            ], resize_keyboard=True)
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    try:
        amount = float(text.replace('$', '').replace(',', ''))
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a valid number (e.g., 50.00)"
        )
        return REQUEST_AMOUNT
    
    if amount <= 0:
        await update.message.reply_text(
            "❌ Amount must be greater than zero."
        )
        return REQUEST_AMOUNT
    
    min_withdrawal = context.user_data.get('min_withdrawal', 10.0)
    user_balance = context.user_data.get('user_balance', 0.0)
    
    if amount < min_withdrawal:
        await update.message.reply_text(
            f"❌ Amount too low!\n\n"
            f"Minimum withdrawal: ${min_withdrawal:.2f}\n"
            f"You requested: ${amount:.2f}\n\n"
            f"Please enter a higher amount."
        )
        return REQUEST_AMOUNT
    
    if amount > user_balance:
        await update.message.reply_text(
            f"❌ Insufficient balance!\n\n"
            f"Your balance: ${user_balance:.2f}\n"
            f"You requested: ${amount:.2f}\n\n"
            f"Please enter a lower amount."
        )
        return REQUEST_AMOUNT
    
    user_id = update.effective_user.id
    
    try:
        stats = db.get_user_stats(user_id)
        payout_method = stats['payout_method']
        payout_details = stats['payout_details']
        
        withdrawal_id = db.create_withdrawal(
            user_id, 
            amount, 
            payout_method, 
            payout_details
        )
        
        if withdrawal_id:
            await update.message.reply_text(
                f"✅ **Withdrawal Request Submitted**\n\n"
                f"💵 Amount: ${amount:.2f}\n"
                f"💳 Method: {payout_method}\n"
                f"🆔 Request ID: #{withdrawal_id}\n\n"
                f"⏳ Your request is now pending admin approval.\n"
                f"You will be notified once it's processed.",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
                    [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
                    [KeyboardButton("💬 Support")]
                ], resize_keyboard=True),
                parse_mode='Markdown'
            )
            
            await notify_admins_new_withdrawal(context, withdrawal_id, amount, user_id)
            
        else:
            await update.message.reply_text(
                "❌ Failed to create withdrawal request. Please try again."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your request. Please try again."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def notify_admins_new_withdrawal(context: ContextTypes.DEFAULT_TYPE, withdrawal_id, amount, user_id):
    try:
        admin_ids = ADMIN_IDS
        user = db.get_user(user_id)
        
        username = user['username'] or "No username"
        name = user['first_name'] or "Unknown"
        
        notification_text = (
            f"🔔 **New Withdrawal Request**\n\n"
            f"🆔 Request ID: #{withdrawal_id}\n"
            f"👤 User: {name} (@{username})\n"
            f"💵 Amount: ${amount:.2f}\n\n"
            f"Use /withdraws pending to manage requests."
        )
        
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Withdrawal cancelled.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
            [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
            [KeyboardButton("💬 Support")]
        ], resize_keyboard=True)
    )
    return ConversationHandler.END
