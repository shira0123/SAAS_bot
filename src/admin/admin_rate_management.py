import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

SET_RATE_VALUE = range(1)

def get_rate_display_name(rate_type):
    """
    Safely converts rate_type key to a readable name.
    Handles NoneType to prevent crashes.
    """
    if not rate_type:
        return "Unknown Plan"
        
    rate_names = {
        'per_view': '💎 Per View (Limited)',
        'per_day_view': '📅 Per Day View (Unlimited)',
        'per_reaction': '❤️ Per Reaction (Limited)',
        'per_day_reaction': '📆 Per Day Reaction (Unlimited)',
        'join_view_n_posts': '🚀 View N Posts & Leave',
        'join_react_n_posts': '🚀 React N Posts & Leave',
        'join_view_recent_post': '⚡ View Recent Post & Leave',
        'join_react_recent_post': '⚡ React Recent Post & Leave'
    }
    
    # Return the mapped name, or format the key if not found
    return rate_names.get(rate_type, str(rate_type).replace('_', ' ').title())

async def show_rate_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the rate management menu with all 8 rates."""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
        if update.callback_query:
            await update.callback_query.answer("⛔ Access denied")
        return

    rates = db.get_saas_rates()
    
    rate_info = "**Current SaaS Rates (per-unit):**\n\n"
    keyboard = []
    
    for rate in rates:
        rate_type = rate['rate_type']
        display_name = get_rate_display_name(rate_type)
        rate_info += f"• {display_name}: ${float(rate['price_per_unit']):.4f}\n"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"rate_{rate_type}")])

    # Add a Back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_back_from_rates")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
⚙️ **Rate Management**

{rate_info}

Select a rate to update:
"""
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
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
    """Handle selection of any rate button."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not db.is_admin(user_id):
        await query.answer("⛔ Access denied")
        return ConversationHandler.END
    
    rate_type = query.data.replace('rate_', '')
    context.user_data['rate_type_to_update'] = rate_type
    
    rate_name = get_rate_display_name(rate_type)
    
    rates = db.get_saas_rates()
    current_rate = next((r for r in rates if r['rate_type'] == rate_type), None)
    current_value = float(current_rate['price_per_unit']) if current_rate else 0
    
    await query.answer()
    
    await query.edit_message_text(
        f"⚙️ **Update {rate_name}**\n\n"
        f"Current rate: ${current_value:.4f}\n\n"
        f"Please enter the new per-unit rate (e.g., 0.0015):\n\n"
        f"Or /cancel to go back.",
        parse_mode='Markdown'
    )
    
    return SET_RATE_VALUE

async def receive_new_rate_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and update the new rate value."""
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id):
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
            await update.message.reply_text("❌ Session expired. Please start again.")
            return ConversationHandler.END
        
        db.update_saas_rate(rate_type, new_value)
        
        rate_name = get_rate_display_name(rate_type)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Rates", callback_data="show_rates")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Rate Updated Successfully!**\n\n"
            f"{rate_name}: ${new_value:.4f}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number format. Please enter a valid decimal number (e.g., 0.0015):\n\n"
            "Or /cancel to go back."
        )
        return SET_RATE_VALUE

async def cancel_rate_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the rate update and show main rates menu."""
    context.user_data.clear()
    if update.callback_query:
        await show_rate_management(update.callback_query, context)
    else:
        await show_rate_management(update, context) 
    
    return ConversationHandler.END

def get_rate_management_handler():
    """Returns the ConversationHandler for rate management."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_rate_to_update, pattern='^rate_')
        ],
        states={
            SET_RATE_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_rate_value)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_rate_update),
            CallbackQueryHandler(cancel_rate_update, pattern='^show_rates$')
        ],
        name="rate_management",
        persistent=False
    )