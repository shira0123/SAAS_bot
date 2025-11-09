import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from src.database.database import Database
from src.database.config import ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

BROADCAST_MESSAGE, ADMIN_USER_ID, ADMIN_ROLE = range(3)

async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show broadcast message menu"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="broadcast_all")],
        [InlineKeyboardButton("💎 Active Buyers", callback_data="broadcast_active")],
        [InlineKeyboardButton("⏰ Expired Buyers", callback_data="broadcast_expired")],
        [InlineKeyboardButton("👔 Resellers", callback_data="broadcast_resellers")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = """
📢 **Broadcast Message**

Send a message to specific user groups:

• **All Users** - Everyone registered
• **Active Buyers** - Users with active plans
• **Expired Buyers** - Users with expired plans
• **Resellers** - All resellers only

Select a target audience:
"""
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast flow"""
    query = update.callback_query
    await query.answer()
    
    target_group = query.data.split('_')[1]
    context.user_data['broadcast_target'] = target_group
    
    target_names = {
        'all': 'All Users',
        'active': 'Active Buyers',
        'expired': 'Expired Buyers',
        'resellers': 'Resellers'
    }
    
    await query.edit_message_text(
        f"📢 **Broadcasting to: {target_names[target_group]}**\n\n"
        f"Send your message now (text, photo, or document).\n\n"
        f"Type /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return BROADCAST_MESSAGE

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and send broadcast message"""
    target_group = context.user_data.get('broadcast_target', 'all')
    
    users = db.get_broadcast_users(target_group)
    
    if not users:
        await update.message.reply_text("❌ No users found in target group.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"📤 Broadcasting to {len(users)} users...",
        parse_mode='Markdown'
    )
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            if update.message.text:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=update.message.text,
                    parse_mode='Markdown' if update.message.text.count('*') > 0 or update.message.text.count('_') > 0 else None
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=user['user_id'],
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=user['user_id'],
                    document=update.message.document.file_id,
                    caption=update.message.caption
                )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to send to user {user['user_id']}: {e}")
    
    await update.message.reply_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"✓ Sent: {success_count}\n"
        f"✗ Failed: {fail_count}\n"
        f"Total: {len(users)}",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast"""
    await update.message.reply_text("❌ Broadcast cancelled.")
    return ConversationHandler.END

async def show_admin_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin management menu (root admin only)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_IDS[0]:
        await update.message.reply_text("❌ Root admin access required.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="admin_add")],
        [InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove")],
        [InlineKeyboardButton("👥 View Admins", callback_data="admin_view")],
        [InlineKeyboardButton("📜 Admin Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = """
👑 **Admin Management**

Manage administrative access:

• **Add Admin** - Grant admin privileges
• **Remove Admin** - Revoke admin access
• **View Admins** - List all administrators
• **Admin Logs** - View admin activity

Select an option:
"""
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add admin flow"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ **Add New Admin**\n\n"
        "Send the user ID of the person to make admin.\n\n"
        "Send /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return ADMIN_USER_ID

async def receive_admin_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user ID to make admin"""
    try:
        user_id = int(update.message.text.strip())
        
        user = db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return ADMIN_USER_ID
        
        if db.is_admin(user_id):
            await update.message.reply_text("❌ User is already an admin.")
            return ConversationHandler.END
        
        db.add_admin(user_id, user.get('username'), 'admin')
        
        await update.message.reply_text(
            f"✅ **Admin Added!**\n\n"
            f"User: @{user.get('username', 'N/A')}\n"
            f"ID: {user_id}\n"
            f"Role: Admin",
            parse_mode='Markdown'
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 **You are now an administrator!**\n\n"
                     "You have been granted admin privileges.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify new admin: {e}")
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please send a number.")
        return ADMIN_USER_ID

async def start_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start remove admin flow"""
    query = update.callback_query
    await query.answer()
    
    admins = db.get_all_admins()
    
    if not admins:
        await query.edit_message_text("No admins to remove.")
        return ConversationHandler.END
    
    message = "❌ **Remove Admin**\n\nCurrent admins:\n\n"
    for admin in admins:
        message += f"• {admin['user_id']} - @{admin.get('username', 'N/A')} ({admin['role']})\n"
    
    message += "\nSend the user ID to remove admin access.\nSend /cancel to abort."
    
    await query.edit_message_text(message, parse_mode='Markdown')
    
    return ADMIN_USER_ID

async def view_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all admins"""
    query = update.callback_query
    await query.answer()
    
    admins = db.get_all_admins()
    
    if not admins:
        await query.edit_message_text("No admins found.")
        return
    
    message = "👥 **All Administrators**\n\n"
    for admin in admins:
        status = "✅ Active" if admin['is_active'] else "❌ Inactive"
        message += f"• **{admin.get('username', 'N/A')}**\n"
        message += f"  └ ID: {admin['user_id']} | Role: {admin['role']} | {status}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_manage")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def view_admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View admin activity logs"""
    query = update.callback_query
    await query.answer()
    
    logs = db.get_admin_logs(limit=20)
    
    if not logs:
        await query.edit_message_text("No admin logs found.")
        return
    
    message = "📜 **Recent Admin Activity**\n\n"
    for log in logs:
        message += f"• {log['created_at'].strftime('%m/%d %H:%M')} - @{log.get('username', 'N/A')}\n"
        message += f"  └ {log['action']}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_manage")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

def get_broadcast_handler():
    """Get broadcast conversation handler"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern='^broadcast_')],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_broadcast_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel_broadcast)],
        name="broadcast",
        persistent=False,
        per_message=False
    )

def get_admin_management_handler():
    """Get admin management conversation handler"""
    from telegram.ext import filters, MessageHandler, CallbackQueryHandler
    
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_admin, pattern='^admin_add$'),
            CallbackQueryHandler(start_remove_admin, pattern='^admin_remove$')
        ],
        states={
            ADMIN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_user_id)]
        },
        fallbacks=[CommandHandler('cancel', cancel_broadcast)],
        name="admin_management",
        persistent=False,
        per_message=False
    )
