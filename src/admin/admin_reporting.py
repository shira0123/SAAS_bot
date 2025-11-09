import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

async def accsell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "📊 **View User Seller Stats**\n\n"
            "**Usage:** /accsell <username>\n"
            "**Example:** /accsell @johndoe",
            parse_mode='Markdown'
        )
        return
    
    username = context.args[0].replace('@', '')
    
    user = db.get_user_by_username(username)
    
    if not user:
        await update.message.reply_text(f"❌ User @{username} not found in database.")
        return
    
    stats = db.get_user_detailed_stats(user['user_id'])
    
    if not stats:
        await update.message.reply_text(f"❌ Unable to retrieve stats for @{username}.")
        return
    
    status_emoji = "🚫" if stats['is_banned'] else "✅"
    withdraw_emoji = "✅" if stats['can_withdraw'] else "🚫"
    
    message = f"""
📊 **Seller Stats for @{username}**

👤 **User Info:**
• User ID: `{stats['user_id']}`
• Name: {stats['first_name'] or 'N/A'} {stats['last_name'] or ''}
• Status: {status_emoji} {'Banned' if stats['is_banned'] else 'Active'}
• Can Withdraw: {withdraw_emoji}
• Joined: {stats['created_at'].strftime('%Y-%m-%d')}

💰 **Financial:**
• Seller Balance: ${stats['seller_balance']:.2f}
• Total Withdrawn: ${stats['total_withdrawn']:.2f}
• Referral Earnings: ${stats['referral_earnings']:.2f}

📱 **Accounts:**
• Total Sold: {stats['accounts_sold']}
• Banned Accounts: {stats['banned_accounts']}

🎁 **Referrals:**
• Total Referrals: {stats['referral_count']}
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def alluser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    users = db.get_all_users_stats(limit=limit, offset=offset)
    total_users = db.get_total_users_count()
    total_pages = (total_users + limit - 1) // limit
    
    if not users:
        await update.message.reply_text("📊 No users found.")
        return
    
    message = f"📊 **All Users Stats** (Page {page}/{total_pages})\n\n"
    
    for user in users:
        username = f"@{user['username']}" if user['username'] else f"ID:{user['user_id']}"
        status = "🚫" if user['is_banned'] else "✅"
        
        message += f"{status} **{username}**\n"
        message += f"└ Balance: ${user['seller_balance']:.2f} | "
        message += f"Sold: {user['accounts_sold']} | "
        message += f"Refs: {user['referral_count']}\n\n"
    
    if total_pages > 1:
        message += f"\n**Navigation:**\n"
        if page > 1:
            message += f"Previous: /alluser {page - 1}\n"
        if page < total_pages:
            message += f"Next: /alluser {page + 1}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    stats = db.get_system_stats()
    
    if not stats:
        await update.message.reply_text("❌ Unable to retrieve system stats.")
        return
    
    message = f"""
📊 **System Statistics**

👥 **Users:**
• Total Users: {stats['total_users']}
• Banned Users: {stats['banned_users']}

📱 **Accounts:**
• Total Sold: {stats['total_accounts_sold']}
• Active Accounts: {stats['active_accounts']}
• Banned Accounts: {stats['banned_accounts']}

💰 **Financials:**
• Total Seller Balance: ${stats['total_seller_balance']:.2f}
• Total Withdrawn: ${stats['total_withdrawn']:.2f}
• Total Referral Earnings: ${stats['total_referral_earnings']:.2f}

💸 **Withdrawals:**
• Pending Withdrawals: {stats['pending_withdrawals']}
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def setref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    if not context.args or len(context.args) != 1:
        current_commission = db.get_referral_commission()
        await update.message.reply_text(
            f"🎁 **Current Referral Commission:** {current_commission * 100:.1f}%\n\n"
            "**Usage:** /setref <percentage>\n"
            "**Example:** /setref 15 (for 15%)",
            parse_mode='Markdown'
        )
        return
    
    try:
        percentage = float(context.args[0])
        
        if percentage < 0 or percentage > 100:
            await update.message.reply_text("❌ Percentage must be between 0 and 100.")
            return
        
        decimal_value = percentage / 100
        db.set_referral_commission(decimal_value)
        
        await update.message.reply_text(
            f"✅ **Referral Commission Updated!**\n\n"
            f"New commission: {percentage:.1f}%\n\n"
            "This will apply to all future account sales.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid percentage format. Please use a number (e.g., 15)")
