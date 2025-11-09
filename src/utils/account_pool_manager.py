import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

ADD_PHONE, ADD_SESSION = range(2)

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    page = 1
    if context.args and len(context.args) > 0:
        try:
            page = int(context.args[0])
            if page < 1:
                page = 1
        except ValueError:
            page = 1
    
    limit = 10
    offset = (page - 1) * limit
    
    stats = db.get_account_pool_stats()
    accounts = db.get_all_accounts(limit=limit, offset=offset)
    
    message = f"""
📱 **Account Pool Manager**

📊 **Pool Statistics:**
• Total Accounts: {stats['total_accounts']}
• ✅ Active & Ready: {stats['active_accounts']}
• 🚫 Banned: {stats['banned_accounts']}
• 📦 Full: {stats['full_accounts']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Accounts (Page {page}):**

"""
    
    if not accounts:
        message += "No accounts found.\n"
    else:
        for acc in accounts:
            status_emoji = "✅" if acc['account_status'] == 'active' and not acc['is_banned'] else "🚫" if acc['is_banned'] else "📦"
            join_info = f"{acc['join_count']}/{acc['max_joins']}"
            last_used = acc['last_used'].strftime('%Y-%m-%d %H:%M') if acc['last_used'] else 'Never'
            
            message += f"{status_emoji} **ID {acc['id']}** | {acc['phone_number']}\n"
            message += f"  └ Joins: {join_info} | Status: {acc['account_status']} | Last: {last_used}\n\n"
    
    message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Commands:**
• /addaccount - Manually add a new account
• /removeaccount <id> - Remove an account
• /checkaccounts - Check all account statuses

"""
    
    total_accounts = stats['total_accounts']
    total_pages = (total_accounts + limit - 1) // limit
    
    if total_pages > 1:
        if page > 1:
            message += f"Previous: /accounts {page - 1}\n"
        if page < total_pages:
            message += f"Next: /accounts {page + 1}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def start_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📱 **Add New Account Manually**\n\n"
        "Please send the **phone number** (e.g., +1234567890)\n\n"
        "Or /cancel to stop."
    )
    return ADD_PHONE

async def receive_add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data['add_phone'] = phone
    
    await update.message.reply_text(
        f"✅ Phone: {phone}\n\n"
        "Now please send the **session string** for this account.\n\n"
        "Or /cancel to stop."
    )
    return ADD_SESSION

async def receive_add_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_string = update.message.text.strip()
    phone = context.user_data.get('add_phone')
    
    if not phone:
        await update.message.reply_text("❌ Error: Phone number not found. Please start over with /addaccount")
        return ConversationHandler.END
    
    try:
        account_id = db.add_account_manual(phone, session_string)
        
        await update.message.reply_text(
            f"✅ **Account Added Successfully!**\n\n"
            f"Account ID: #{account_id}\n"
            f"Phone: {phone}\n"
            f"Status: Active\n\n"
            "The account is now available in the pool for service delivery."
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        await update.message.reply_text(
            f"❌ Error adding account: {str(e)}\n\n"
            "Please try again or contact support."
        )
        return ConversationHandler.END

async def cancel_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Account addition cancelled.")
    return ConversationHandler.END

async def remove_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "**Usage:** /removeaccount <account_id>\n"
            "**Example:** /removeaccount 123",
            parse_mode='Markdown'
        )
        return
    
    try:
        account_id = int(context.args[0])
        account = db.get_account_by_id(account_id)
        
        if not account:
            await update.message.reply_text(f"❌ Account #{account_id} not found.")
            return
        
        db.remove_account(account_id)
        
        await update.message.reply_text(
            f"✅ **Account Removed**\n\n"
            f"Account ID: #{account_id}\n"
            f"Phone: {account['phone_number']}\n\n"
            "The account has been permanently removed from the pool."
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid account ID. Please provide a number.")
    except Exception as e:
        logger.error(f"Error removing account: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
