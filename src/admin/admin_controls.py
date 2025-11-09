import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from src.database.database import Database
from src.database.config import ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

async def list_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized. Admin access only.")
        return
    
    try:
        withdrawals = db.get_pending_withdrawals()
        
        if not withdrawals:
            await update.message.reply_text(
                "📭 **No Pending Withdrawals**\n\n"
                "There are currently no withdrawal requests waiting for approval.",
                parse_mode='Markdown'
            )
            return
        
        message_text = f"📋 **Pending Withdrawal Requests** ({len(withdrawals)})\n\n"
        
        buttons = []
        for w in withdrawals:
            username = w['username'] or "No username"
            name = w['first_name'] or "Unknown"
            amount = float(w['amount'])
            withdrawal_id = w['id']
            
            message_text += (
                f"🆔 #{withdrawal_id} - {name} (@{username})\n"
                f"💵 ${amount:.2f}\n"
                f"📅 {w['requested_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            )
            
            buttons.append([
                InlineKeyboardButton(
                    f"#{withdrawal_id} - ${amount:.2f} - @{username}",
                    callback_data=f"withdrawal_view_{withdrawal_id}"
                )
            ])
        
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error listing withdrawals: {e}")
        await update.message.reply_text(
            "❌ An error occurred while fetching withdrawal requests."
        )

async def view_withdrawal_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Unauthorized. Admin access only.")
        return
    
    try:
        withdrawal_id = int(query.data.split('_')[2])
        withdrawal = db.get_withdrawal_by_id(withdrawal_id)
        
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal request not found.")
            return
        
        username = withdrawal['username'] or "No username"
        name = withdrawal['first_name'] or "Unknown"
        amount = float(withdrawal['amount'])
        balance = float(withdrawal['seller_balance'])
        referral_earnings = float(withdrawal['referral_earnings'])
        total_withdrawn = float(withdrawal['total_withdrawn'])
        payout_method = withdrawal['payout_method'] or "Not set"
        payout_details = withdrawal['payout_details'] or "Not set"
        
        accounts_sold = db.get_user_accounts_count(withdrawal['user_id'])
        banned_accounts = db.get_banned_accounts_count(withdrawal['user_id'])
        
        detail_text = (
            f"🆔 **Withdrawal Request #{withdrawal_id}**\n\n"
            f"👤 **User Information:**\n"
            f"Name: {name}\n"
            f"Username: @{username}\n"
            f"User ID: {withdrawal['user_id']}\n\n"
            f"💰 **Account Stats:**\n"
            f"Current Balance: ${balance:.2f}\n"
            f"Referral Earnings: ${referral_earnings:.2f}\n"
            f"Total Withdrawn: ${total_withdrawn:.2f}\n"
            f"Accounts Sold: {accounts_sold}\n"
            f"Banned Accounts: {banned_accounts}\n\n"
            f"💸 **Withdrawal Details:**\n"
            f"Requested Amount: ${amount:.2f}\n"
            f"Payout Method: {payout_method}\n"
            f"Payout Details: {payout_details}\n"
            f"Requested: {withdrawal['requested_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            "Choose an action:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"withdrawal_approve_{withdrawal_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"withdrawal_reject_{withdrawal_id}")
            ],
            [InlineKeyboardButton("🔙 Back to List", callback_data="withdrawal_back")]
        ]
        
        await query.edit_message_text(
            detail_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error viewing withdrawal detail: {e}")
        await query.edit_message_text(
            "❌ An error occurred while loading withdrawal details."
        )

async def approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Unauthorized. Admin access only.")
        return
    
    try:
        withdrawal_id = int(query.data.split('_')[2])
        withdrawal = db.get_withdrawal_by_id(withdrawal_id)
        
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal request not found.")
            return
        
        if withdrawal['status'] != 'pending':
            await query.edit_message_text(
                f"⚠️ This withdrawal has already been {withdrawal['status']}."
            )
            return
        
        amount = float(withdrawal['amount'])
        balance = float(withdrawal['seller_balance'])
        
        if amount > balance:
            await query.edit_message_text(
                f"❌ **Cannot Approve**\n\n"
                f"Withdrawal amount (${amount:.2f}) exceeds user's balance (${balance:.2f}).\n\n"
                f"This withdrawal must be rejected.",
                parse_mode='Markdown'
            )
            return
        
        success = db.approve_withdrawal(withdrawal_id, user_id, "Approved by admin")
        
        if success:
            await query.edit_message_text(
                f"✅ **Withdrawal Approved**\n\n"
                f"Request ID: #{withdrawal_id}\n"
                f"Amount: ${amount:.2f}\n"
                f"User: @{withdrawal['username']}\n\n"
                f"The user has been notified.",
                parse_mode='Markdown'
            )
            
            try:
                await context.bot.send_message(
                    chat_id=withdrawal['user_id'],
                    text=(
                        f"✅ **Withdrawal Approved**\n\n"
                        f"Your withdrawal request of ${amount:.2f} has been approved!\n"
                        f"Request ID: #{withdrawal_id}\n\n"
                        f"The amount will be sent to your {withdrawal['payout_method']} shortly.\n"
                        f"Thank you for your patience!"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
        else:
            await query.edit_message_text(
                "❌ Failed to approve withdrawal. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        await query.edit_message_text(
            "❌ An error occurred while approving the withdrawal."
        )

async def reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Unauthorized. Admin access only.")
        return
    
    try:
        withdrawal_id = int(query.data.split('_')[2])
        withdrawal = db.get_withdrawal_by_id(withdrawal_id)
        
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal request not found.")
            return
        
        if withdrawal['status'] != 'pending':
            await query.edit_message_text(
                f"⚠️ This withdrawal has already been {withdrawal['status']}."
            )
            return
        
        amount = float(withdrawal['amount'])
        
        success = db.reject_withdrawal(withdrawal_id, user_id, "Rejected by admin")
        
        if success:
            await query.edit_message_text(
                f"❌ **Withdrawal Rejected**\n\n"
                f"Request ID: #{withdrawal_id}\n"
                f"Amount: ${amount:.2f}\n"
                f"User: @{withdrawal['username']}\n\n"
                f"The user has been notified.",
                parse_mode='Markdown'
            )
            
            try:
                await context.bot.send_message(
                    chat_id=withdrawal['user_id'],
                    text=(
                        f"❌ **Withdrawal Rejected**\n\n"
                        f"Your withdrawal request of ${amount:.2f} has been rejected.\n"
                        f"Request ID: #{withdrawal_id}\n\n"
                        f"If you believe this is an error, please contact support."
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
        else:
            await query.edit_message_text(
                "❌ Failed to reject withdrawal. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await query.edit_message_text(
            "❌ An error occurred while rejecting the withdrawal."
        )

async def back_to_withdrawal_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        withdrawals = db.get_pending_withdrawals()
        
        if not withdrawals:
            await query.edit_message_text(
                "📭 **No Pending Withdrawals**\n\n"
                "There are currently no withdrawal requests waiting for approval.",
                parse_mode='Markdown'
            )
            return
        
        message_text = f"📋 **Pending Withdrawal Requests** ({len(withdrawals)})\n\n"
        
        buttons = []
        for w in withdrawals:
            username = w['username'] or "No username"
            name = w['first_name'] or "Unknown"
            amount = float(w['amount'])
            withdrawal_id = w['id']
            
            message_text += (
                f"🆔 #{withdrawal_id} - {name} (@{username})\n"
                f"💵 ${amount:.2f}\n"
                f"📅 {w['requested_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            )
            
            buttons.append([
                InlineKeyboardButton(
                    f"#{withdrawal_id} - ${amount:.2f} - @{username}",
                    callback_data=f"withdrawal_view_{withdrawal_id}"
                )
            ])
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error returning to list: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please use /withdraws pending to view requests."
        )

async def set_withdrawal_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized. Admin access only.")
        return
    
    if not context.args:
        current_limits = db.get_withdrawal_limits()
        limits_text = ', '.join([f"${x:.2f}" for x in current_limits])
        
        await update.message.reply_text(
            f"📊 **Current Withdrawal Limits**\n\n"
            f"{limits_text}\n\n"
            f"To update, use:\n"
            f"/withdrawlimit 10,50,100,500,5000",
            parse_mode='Markdown'
        )
        return
    
    try:
        limits_str = ' '.join(context.args)
        limits = [float(x.strip()) for x in limits_str.split(',')]
        
        if len(limits) < 1:
            await update.message.reply_text(
                "❌ Please provide at least one limit value."
            )
            return
        
        for limit in limits:
            if limit <= 0:
                await update.message.reply_text(
                    "❌ All limits must be positive numbers."
                )
                return
        
        db.set_withdrawal_limits(limits)
        
        limits_text = ', '.join([f"${x:.2f}" for x in limits])
        
        await update.message.reply_text(
            f"✅ **Withdrawal Limits Updated**\n\n"
            f"New limits: {limits_text}\n\n"
            f"These will apply to new withdrawal requests.",
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Use:\n"
            "/withdrawlimit 10,50,100,500,5000"
        )
    except Exception as e:
        logger.error(f"Error setting withdrawal limits: {e}")
        await update.message.reply_text(
            "❌ An error occurred while updating limits."
        )

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized. Admin access only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /ban <username>\n"
            "Example: /ban john_doe"
        )
        return
    
    username = context.args[0].replace('@', '')
    
    try:
        user = db.get_user_by_username(username)
        
        if not user:
            await update.message.reply_text(
                f"❌ User @{username} not found in the database."
            )
            return
        
        if user['is_banned']:
            await update.message.reply_text(
                f"⚠️ User @{username} is already banned."
            )
            return
        
        db.ban_user(user['user_id'])
        
        await update.message.reply_text(
            f"🚫 **User Banned**\n\n"
            f"Username: @{username}\n"
            f"User ID: {user['user_id']}\n\n"
            f"The user can no longer use the bot.",
            parse_mode='Markdown'
        )
        
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=(
                    "🚫 **Account Suspended**\n\n"
                    "Your account has been suspended.\n"
                    "Please contact support if you believe this is an error."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify banned user: {e}")
            
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await update.message.reply_text(
            "❌ An error occurred while banning the user."
        )

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized. Admin access only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /unban <username>\n"
            "Example: /unban john_doe"
        )
        return
    
    username = context.args[0].replace('@', '')
    
    try:
        user = db.get_user_by_username(username)
        
        if not user:
            await update.message.reply_text(
                f"❌ User @{username} not found in the database."
            )
            return
        
        if not user['is_banned']:
            await update.message.reply_text(
                f"⚠️ User @{username} is not banned."
            )
            return
        
        db.unban_user(user['user_id'])
        
        await update.message.reply_text(
            f"✅ **User Unbanned**\n\n"
            f"Username: @{username}\n"
            f"User ID: {user['user_id']}\n\n"
            f"The user can now use the bot again.",
            parse_mode='Markdown'
        )
        
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=(
                    "✅ **Account Restored**\n\n"
                    "Your account has been restored.\n"
                    "You can now use the bot normally."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify unbanned user: {e}")
            
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        await update.message.reply_text(
            "❌ An error occurred while unbanning the user."
        )

async def stop_withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized. Admin access only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /stopwithdraw <username>\n"
            "Example: /stopwithdraw john_doe"
        )
        return
    
    username = context.args[0].replace('@', '')
    
    try:
        user = db.get_user_by_username(username)
        
        if not user:
            await update.message.reply_text(
                f"❌ User @{username} not found in the database."
            )
            return
        
        if not user['can_withdraw']:
            await update.message.reply_text(
                f"⚠️ Withdrawals are already disabled for @{username}."
            )
            return
        
        db.set_withdraw_permission(user['user_id'], False)
        
        await update.message.reply_text(
            f"🚫 **Withdrawals Disabled**\n\n"
            f"Username: @{username}\n"
            f"User ID: {user['user_id']}\n\n"
            f"The user can no longer request withdrawals.",
            parse_mode='Markdown'
        )
        
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=(
                    "⚠️ **Withdrawals Disabled**\n\n"
                    "Withdrawal functionality has been disabled for your account.\n"
                    "Please contact support for more information."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
            
    except Exception as e:
        logger.error(f"Error stopping withdrawals: {e}")
        await update.message.reply_text(
            "❌ An error occurred while updating withdrawal permissions."
        )

async def allow_withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized. Admin access only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /allowwithdraw <username>\n"
            "Example: /allowwithdraw john_doe"
        )
        return
    
    username = context.args[0].replace('@', '')
    
    try:
        user = db.get_user_by_username(username)
        
        if not user:
            await update.message.reply_text(
                f"❌ User @{username} not found in the database."
            )
            return
        
        if user['can_withdraw']:
            await update.message.reply_text(
                f"⚠️ Withdrawals are already enabled for @{username}."
            )
            return
        
        db.set_withdraw_permission(user['user_id'], True)
        
        await update.message.reply_text(
            f"✅ **Withdrawals Enabled**\n\n"
            f"Username: @{username}\n"
            f"User ID: {user['user_id']}\n\n"
            f"The user can now request withdrawals.",
            parse_mode='Markdown'
        )
        
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=(
                    "✅ **Withdrawals Enabled**\n\n"
                    "Withdrawal functionality has been enabled for your account.\n"
                    "You can now request withdrawals."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
            
    except Exception as e:
        logger.error(f"Error enabling withdrawals: {e}")
        await update.message.reply_text(
            "❌ An error occurred while updating withdrawal permissions."
        )
