import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from database import Database

logger = logging.getLogger(__name__)

db = Database()

SET_MARGIN, WITHDRAW_AMOUNT = range(2)

async def show_reseller_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not db.is_reseller(user.id):
        await update.message.reply_text(
            "❌ **Not a Reseller**\n\n"
            "You don't have access to the reseller panel.\n"
            "Contact admin to become a reseller."
        )
        return
    
    reseller_info = db.get_reseller_info(user.id)
    user_data = db.get_user(user.id)
    
    keyboard = [
        [KeyboardButton("💼 Create Plan Link"), KeyboardButton("📊 My Sales")],
        [KeyboardButton("⚙️ Set Margin"), KeyboardButton("💸 Withdraw Commission")],
        [KeyboardButton("🔙 Back to Buyer Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message = f"""
👔 **Reseller Panel**

💰 **Total Sales:** ${reseller_info['total_sales']:.2f}
💵 **Total Profit:** ${reseller_info['total_profit']:.2f}
📊 **Current Margin:** {reseller_info['margin_percentage']:.1f}%

**How it works:**
1. Create custom plan links with your margin
2. Share links with customers
3. Earn profit on each sale
4. Withdraw your commission

Use the menu below:
"""
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def create_plan_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reseller_info = db.get_reseller_info(user.id)
    
    base_link = f"https://t.me/{context.bot.username}?start=reseller_{user.id}"
    
    message = f"""
💼 **Create Plan Link**

**Your Reseller Link:**
`{base_link}`

**Your Margin:** {reseller_info['margin_percentage']:.1f}%

Share this link with customers. When they purchase a plan through your link, you'll earn {reseller_info['margin_percentage']:.1f}% commission on the sale.

**Example:**
If customer buys a $100 plan, you earn ${(100 * reseller_info['margin_percentage'] / 100):.2f}
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reseller_info = db.get_reseller_info(user.id)
    
    message = f"""
📊 **My Sales**

💰 **Total Sales:** ${reseller_info['total_sales']:.2f}
💵 **Total Profit:** ${reseller_info['total_profit']:.2f}
📊 **Margin:** {reseller_info['margin_percentage']:.1f}%
🎯 **Status:** {'✅ Active' if reseller_info['is_active'] else '❌ Inactive'}

Keep sharing your link to increase your earnings!
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def start_set_margin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reseller_info = db.get_reseller_info(user.id)
    
    await update.message.reply_text(
        f"⚙️ **Set Your Margin**\n\n"
        f"Current margin: {reseller_info['margin_percentage']:.1f}%\n\n"
        f"Enter your new margin percentage (5-30%):\n"
        f"Example: 15\n\n"
        f"Send /cancel to abort."
    )
    
    return SET_MARGIN

async def receive_margin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        margin = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Invalid margin. Please enter a number.")
        return SET_MARGIN
    
    if margin < 5 or margin > 30:
        await update.message.reply_text("❌ Margin must be between 5% and 30%.")
        return SET_MARGIN
    
    result = db.update_reseller_margin(user.id, margin)
    
    if result:
        await update.message.reply_text(
            f"✅ **Margin Updated!**\n\n"
            f"New margin: {margin:.1f}%\n\n"
            f"All future sales will use this margin."
        )
    else:
        await update.message.reply_text("❌ Failed to update margin.")
    
    return ConversationHandler.END

async def start_withdraw_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reseller_info = db.get_reseller_info(user.id)
    user_data = db.get_user(user.id)
    
    if not user_data.get('payout_method'):
        await update.message.reply_text(
            "❌ **Payout Info Not Set**\n\n"
            "Please set your payout info first using the '💳 Set Payout Info' button in seller menu."
        )
        return ConversationHandler.END
    
    min_withdrawal = 10.00
    balance = float(reseller_info['total_profit'])
    
    if balance < min_withdrawal:
        await update.message.reply_text(
            f"❌ **Insufficient Balance**\n\n"
            f"Minimum withdrawal: ${min_withdrawal:.2f}\n"
            f"Your profit: ${balance:.2f}"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"💸 **Withdraw Commission**\n\n"
        f"💰 **Available Profit:** ${balance:.2f}\n"
        f"💳 **Method:** {user_data.get('payout_method', 'Not set')}\n\n"
        f"Enter amount to withdraw (Min: ${min_withdrawal:.2f}):\n\n"
        f"Send /cancel to abort."
    )
    
    return WITHDRAW_AMOUNT

async def receive_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reseller_info = db.get_reseller_info(user.id)
    user_data = db.get_user(user.id)
    
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")
        return WITHDRAW_AMOUNT
    
    balance = float(reseller_info['total_profit'])
    
    if amount < 10.00:
        await update.message.reply_text("❌ Minimum withdrawal is $10.00")
        return WITHDRAW_AMOUNT
    
    if amount > balance:
        await update.message.reply_text(f"❌ Amount exceeds your profit (${balance:.2f})")
        return WITHDRAW_AMOUNT
    
    withdrawal = db.create_reseller_withdrawal(
        user.id,
        amount,
        user_data.get('payout_method'),
        user_data.get('payout_details')
    )
    
    if withdrawal:
        await update.message.reply_text(
            f"✅ **Withdrawal Request Submitted!**\n\n"
            f"**Amount:** ${amount:.2f}\n"
            f"**Request ID:** #{withdrawal['id']}\n\n"
            f"Pending admin approval. You'll be notified once processed."
        )
    else:
        await update.message.reply_text("❌ Failed to create withdrawal request.")
    
    return ConversationHandler.END

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action cancelled.")
    return ConversationHandler.END

def get_reseller_panel_handler():
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^⚙️ Set Margin$"), start_set_margin),
            MessageHandler(filters.Regex("^💸 Withdraw Commission$"), start_withdraw_commission)
        ],
        states={
            SET_MARGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_margin)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_withdraw_amount)]
        },
        fallbacks=[MessageHandler(filters.Regex("^/cancel$"), cancel_action)]
    )
