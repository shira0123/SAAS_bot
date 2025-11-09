import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

db = Database()

CREATE_CODE, DELETE_CODE, CODE_PARAMS = range(3)

async def show_promo_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show promo code management menu"""
    keyboard = [
        [InlineKeyboardButton("➕ Create Promo Code", callback_data="promo_create")],
        [InlineKeyboardButton("❌ Delete Promo Code", callback_data="promo_delete")],
        [InlineKeyboardButton("📊 View All Codes", callback_data="promo_view_all")],
        [InlineKeyboardButton("📜 Usage Logs", callback_data="promo_logs")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = """
🎁 **Promo Code Management**

Manage promotional codes and bonuses for your buyers.

**Options:**
• ➕ **Create Promo Code** - Add new promotional code
• ❌ **Delete Promo Code** - Remove existing code
• 📊 **View All Codes** - See all active codes
• 📜 **Usage Logs** - Track promo code usage

Select an option:
"""
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def create_promo_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start promo code creation"""
    query = update.callback_query
    await query.answer()
    
    message = """
➕ **Create New Promo Code**

Please send promo code details in this format:

```
CODE AMOUNT LIMIT DAYS
```

**Parameters:**
• **CODE** - Promo code name (e.g., WELCOME10, BONUS50)
• **AMOUNT** - Bonus amount in dollars (e.g., 10.00)
• **LIMIT** - Max number of uses (0 for unlimited)
• **DAYS** - Valid for how many days (0 for no expiry)

**Examples:**
```
WELCOME10 10.00 100 30
BONUS50 50.00 50 7
LOYALTY5 5.00 0 0
```

Send the details or /cancel to go back:
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    return CODE_PARAMS

async def receive_promo_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and create promo code"""
    try:
        parts = update.message.text.strip().split()
        
        if len(parts) != 4:
            await update.message.reply_text(
                "❌ Invalid format. Please send: CODE AMOUNT LIMIT DAYS\n"
                "Example: WELCOME10 10.00 100 30"
            )
            return CODE_PARAMS
        
        code = parts[0].upper()
        amount = float(parts[1])
        limit = int(parts[2])
        days = int(parts[3])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0")
            return CODE_PARAMS
        
        if limit < 0 or days < 0:
            await update.message.reply_text("❌ Limit and days cannot be negative")
            return CODE_PARAMS
        
        expires_at = None
        if days > 0:
            expires_at = datetime.now() + timedelta(days=days)
        
        promo_id = db.create_promo_code(
            code=code,
            discount_type='fixed',
            discount_value=amount,
            usage_limit=limit,
            expires_at=expires_at
        )
        
        if promo_id:
            expiry_text = f"{days} days" if days > 0 else "No expiry"
            limit_text = f"{limit} uses" if limit > 0 else "Unlimited"
            
            await update.message.reply_text(
                f"✅ **Promo Code Created Successfully!**\n\n"
                f"**Code:** `{code}`\n"
                f"**Bonus Amount:** ${amount:.2f}\n"
                f"**Usage Limit:** {limit_text}\n"
                f"**Validity:** {expiry_text}\n\n"
                f"Users can now apply this code to receive ${amount:.2f} bonus!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Failed to create promo code. It may already exist."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Amount must be a number.\n"
            "Example: WELCOME10 10.00 100 30"
        )
        return CODE_PARAMS
    except Exception as e:
        logger.error(f"Error creating promo code: {e}")
        await update.message.reply_text(
            "❌ An error occurred while creating the promo code."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def delete_promo_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start promo code deletion"""
    query = update.callback_query
    await query.answer()
    
    message = """
❌ **Delete Promo Code**

Send the promo code you want to delete:

Example: WELCOME10

Or /cancel to go back.
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    return DELETE_CODE

async def receive_delete_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and delete promo code"""
    code = update.message.text.strip().upper()
    
    try:
        db.delete_promo_code(code)
        await update.message.reply_text(
            f"✅ **Promo Code Deleted**\n\n"
            f"Code `{code}` has been removed from the system.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error deleting promo code: {e}")
        await update.message.reply_text(
            f"❌ Failed to delete code `{code}`. It may not exist.",
            parse_mode='Markdown'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def view_all_promo_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all promo codes"""
    query = update.callback_query
    await query.answer()
    
    codes = db.get_all_promo_codes()
    
    if not codes:
        await query.edit_message_text(
            "📊 **No Promo Codes Found**\n\n"
            "Create your first promo code to get started!"
        )
        return
    
    message = "📊 **All Promo Codes**\n\n"
    
    for code in codes:
        status = "✅ Active" if code.get('is_active') else "❌ Inactive"
        limit = code.get('usage_limit', 0)
        used = code.get('times_used', 0)
        limit_text = f"{used}/{limit}" if limit > 0 else f"{used}/∞"
        
        expiry = code.get('expires_at')
        expiry_text = expiry.strftime('%Y-%m-%d') if expiry else "No expiry"
        
        message += f"""
**{code['code']}**
• Amount: ${code.get('discount_value', 0):.2f}
• Status: {status}
• Usage: {limit_text}
• Expires: {expiry_text}

"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )

async def view_promo_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View promo code usage logs"""
    query = update.callback_query
    await query.answer()
    
    logs = db.get_promo_code_usage_logs()
    
    if not logs:
        await query.edit_message_text(
            "📜 **No Usage Logs Found**\n\n"
            "No promo codes have been used yet."
        )
        return
    
    message = "📜 **Promo Code Usage Logs** (Last 20)\n\n"
    
    for i, log in enumerate(logs[:20], 1):
        username = log.get('username', 'N/A')
        code = log.get('code', 'N/A')
        amount = log.get('bonus_amount', 0)
        used_at = log.get('used_at')
        date_text = used_at.strftime('%Y-%m-%d %H:%M') if used_at else 'N/A'
        
        message += f"{i}. @{username} - `{code}` (${amount:.2f}) - {date_text}\n"
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )

async def cancel_promo_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel promo management"""
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ **Cancelled**\n\n"
        "Promo code operation cancelled."
    )
    
    return ConversationHandler.END

def get_promo_management_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_promo_code_start, pattern='^promo_create$'),
            CallbackQueryHandler(delete_promo_code_start, pattern='^promo_delete$'),
            CallbackQueryHandler(view_all_promo_codes, pattern='^promo_view_all$'),
            CallbackQueryHandler(view_promo_logs, pattern='^promo_logs$')
        ],
        states={
            CODE_PARAMS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_params)
            ],
            DELETE_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete_code)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_promo_management)
        ],
        name="promo_management",
        persistent=False,
        per_message=False
    )
