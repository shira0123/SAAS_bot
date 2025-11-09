import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from src.database.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

PAYOUT_METHOD, PAYOUT_DETAILS = range(2)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        stats = db.get_user_stats(user_id)
        accounts_sold = db.get_user_accounts_count(user_id)
        banned_accounts = db.get_banned_accounts_count(user_id)
        
        if not stats:
            await update.message.reply_text("❌ Error loading profile. Please try again.")
            return
        
        seller_balance = float(stats['seller_balance'])
        referral_earnings = float(stats['referral_earnings'])
        total_withdrawn = float(stats['total_withdrawn'])
        lifetime_earnings = seller_balance + total_withdrawn
        
        payout_method = stats['payout_method'] or "Not set"
        payout_details = stats['payout_details'] or "Not set"
        
        profile_text = (
            f"👤 **Your Profile**\n\n"
            f"💰 **Current Balance:** ${seller_balance:.2f}\n"
            f"📊 **Lifetime Earnings:** ${lifetime_earnings:.2f}\n"
            f"💸 **Total Withdrawn:** ${total_withdrawn:.2f}\n"
            f"🎁 **Referral Earnings:** ${referral_earnings:.2f}\n\n"
            f"📱 **Accounts Sold:** {accounts_sold}\n"
            f"🚫 **Banned Accounts:** {banned_accounts}\n\n"
            f"💳 **Payout Method:** {payout_method}\n"
            f"📝 **Payout Details:** {payout_details}\n\n"
            "Use the button below to update your payout information."
        )
        
        keyboard = [
            [KeyboardButton("💳 Set Payout Info")],
            [KeyboardButton("🔙 Back to Menu")]
        ]
        
        await update.message.reply_text(
            profile_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing profile: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading your profile. Please try again."
        )

async def start_set_payout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 **Set Payout Information**\n\n"
        "To withdraw your earnings, we need your payout details.\n\n"
        "Please select your preferred payout method:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("UPI"), KeyboardButton("Bank Transfer")],
            [KeyboardButton("PayPal"), KeyboardButton("Other")],
            [KeyboardButton("❌ Cancel")]
        ], resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return PAYOUT_METHOD

async def receive_payout_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text.strip()
    
    if method == "❌ Cancel":
        await update.message.reply_text(
            "❌ Cancelled. Returning to menu.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
                [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
                [KeyboardButton("💬 Support")]
            ], resize_keyboard=True)
        )
        return ConversationHandler.END
    
    if method not in ["UPI", "Bank Transfer", "PayPal", "Other"]:
        await update.message.reply_text(
            "❌ Invalid method. Please select from the buttons provided."
        )
        return PAYOUT_METHOD
    
    context.user_data['payout_method'] = method
    
    if method == "UPI":
        prompt = "Please enter your UPI ID (e.g., yourname@paytm):"
    elif method == "Bank Transfer":
        prompt = "Please enter your bank account details (Account Number, IFSC, Bank Name):"
    elif method == "PayPal":
        prompt = "Please enter your PayPal email address:"
    else:
        prompt = "Please enter your payout details:"
    
    await update.message.reply_text(
        prompt,
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("❌ Cancel")]
        ], resize_keyboard=True)
    )
    return PAYOUT_DETAILS

async def receive_payout_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    
    if details == "❌ Cancel":
        await update.message.reply_text(
            "❌ Cancelled. Returning to menu.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
                [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
                [KeyboardButton("💬 Support")]
            ], resize_keyboard=True)
        )
        return ConversationHandler.END
    
    if len(details) < 3:
        await update.message.reply_text(
            "❌ Details too short. Please provide valid information."
        )
        return PAYOUT_DETAILS
    
    method = context.user_data.get('payout_method')
    user_id = update.effective_user.id
    
    try:
        db.set_payout_info(user_id, method, details)
        
        await update.message.reply_text(
            f"✅ **Payout Information Saved**\n\n"
            f"Method: {method}\n"
            f"Details: {details}\n\n"
            "You can now request withdrawals!",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
                [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
                [KeyboardButton("💬 Support")]
            ], resize_keyboard=True),
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error saving payout info: {e}")
        await update.message.reply_text(
            "❌ An error occurred while saving your information. Please try again."
        )
        return ConversationHandler.END

async def cancel_payout_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled. Returning to menu.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💸 Withdraw")],
            [KeyboardButton("👤 Profile"), KeyboardButton("🎁 Refer & Earn")],
            [KeyboardButton("💬 Support")]
        ], resize_keyboard=True)
    )
    return ConversationHandler.END
