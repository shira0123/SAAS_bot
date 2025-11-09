import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database
from src.database.config import ADMIN_IDS

logger = logging.getLogger(__name__)

db = Database()

SET_RATE_VALUE = range(1)

async def show_rate_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        if query:
            await query.answer("⛔ Access denied")
        return
    
    rates = db.get_saas_rates()
    
    rate_info = "**Current SaaS Rates:**\n\n"
    for rate in rates:
        rate_info += f"• {rate['rate_type'].replace('_', ' ').title()}: ${rate['price_per_unit']:.4f}\n"
    
    keyboard = [
        [InlineKeyboardButton("💎 Per View Rate", callback_data="rate_per_view")],
        [InlineKeyboardButton("📅 Per Day View Rate", callback_data="rate_per_day_view")],
        [InlineKeyboardButton("❤️ Per Reaction Rate", callback_data="rate_per_reaction")],
        [InlineKeyboardButton("📆 Per Day Reaction Rate", callback_data="rate_per_day_reaction")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
⚙️ **Rate Management**

{rate_info}

Select a rate to update:
"""
    
    if query:
        await query.answer()
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def select_rate_to_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer("⛔ Access denied")
        return ConversationHandler.END
    
    rate_type = query.data.replace('rate_', '')
    context.user_data['rate_type_to_update'] = rate_type
    
    rate_names = {
        'per_view': 'Per View',
        'per_day_view': 'Per Day View',
        'per_reaction': 'Per Reaction',
        'per_day_reaction': 'Per Day Reaction'
    }
    
    rate_name = rate_names.get(rate_type, rate_type)
    
    rates = db.get_saas_rates()
    current_rate = next((r for r in rates if r['rate_type'] == rate_type), None)
    current_value = current_rate['price_per_unit'] if current_rate else 0
    
    await query.answer()
    await query.edit_message_text(
        f"⚙️ **Update {rate_name} Rate**\n\n"
        f"Current rate: ${current_value:.4f}\n\n"
        f"Please enter the new rate value (e.g., 0.001):\n\n"
        f"Or /cancel to go back.",
        parse_mode='Markdown'
    )
    
    return SET_RATE_VALUE

async def receive_new_rate_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Access denied")
        return ConversationHandler.END
    
    try:
        new_value = float(update.message.text.strip())
        
        if new_value < 0:
            await update.message.reply_text(
                "❌ Rate must be a positive number. Please try again or /cancel:"
            )
            return SET_RATE_VALUE
        
        rate_type = context.user_data.get('rate_type_to_update')
        
        if not rate_type:
            await update.message.reply_text(
                "❌ Session expired. Please start again."
            )
            return ConversationHandler.END
        
        db.update_saas_rate(rate_type, new_value)
        
        rate_names = {
            'per_view': 'Per View',
            'per_day_view': 'Per Day View',
            'per_reaction': 'Per Reaction',
            'per_day_reaction': 'Per Day Reaction'
        }
        
        rate_name = rate_names.get(rate_type, rate_type)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Rates", callback_data="show_rates")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Rate Updated Successfully!**\n\n"
            f"{rate_name} Rate: ${new_value:.4f}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number format. Please enter a valid decimal number (e.g., 0.001):\n\n"
            "Or /cancel to go back."
        )
        return SET_RATE_VALUE

async def cancel_rate_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Rates", callback_data="show_rates")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "❌ Rate update cancelled.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

def get_rate_management_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_rate_to_update, pattern='^rate_(per_view|per_day_view|per_reaction|per_day_reaction)$')
        ],
        states={
            SET_RATE_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_rate_value)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_rate_update)
        ],
        name="rate_management",
        persistent=False
    )
