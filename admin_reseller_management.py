import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from database import Database

logger = logging.getLogger(__name__)

db = Database()

APPROVE_USER, SET_COMMISSION = range(2)

async def reseller_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not db.is_admin(user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 View Resellers", callback_data="admin_view_resellers")],
        [InlineKeyboardButton("✅ Approve Reseller", callback_data="admin_approve_reseller")],
        [InlineKeyboardButton("💰 Pending Withdrawals", callback_data="admin_reseller_withdrawals")],
        [InlineKeyboardButton("📊 Commission Summary", callback_data="admin_commission_summary")],
        [InlineKeyboardButton("⚙️ Set Commission Rate", callback_data="admin_set_commission")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "👔 **Reseller Management**\n\nSelect an option:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def view_resellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    resellers = db.get_all_resellers(active_only=False)
    
    if not resellers:
        await query.edit_message_text("No resellers found.")
        return
    
    message = "👥 **All Resellers**\n\n"
    
    for r in resellers[:15]:
        status = "✅ Active" if r['is_active'] else "❌ Inactive"
        message += f"**{r.get('first_name', 'User')}** (@{r.get('username', 'N/A')})\n"
        message += f"  • ID: {r['user_id']}\n"
        message += f"  • Status: {status}\n"
        message += f"  • Margin: {r['margin_percentage']:.1f}%\n"
        message += f"  • Sales: ${r['total_sales']:.2f}\n"
        message += f"  • Profit: ${r['total_profit']:.2f}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_reseller_menu")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def approve_reseller_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "✅ **Approve Reseller**\n\n"
        "Send the user ID of the person to approve as a reseller.\n\n"
        "Send /cancel to abort."
    )
    
    return APPROVE_USER

async def approve_reseller_receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        user_id_to_approve = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please enter a numeric ID.")
        return APPROVE_USER
    
    result = db.approve_reseller_application(user_id_to_approve, user.id)
    
    if result:
        await update.message.reply_text(
            f"✅ **Reseller Approved!**\n\n"
            f"User ID: {user_id_to_approve}\n"
            f"Margin: {result['margin_percentage']:.1f}%\n\n"
            f"The user can now access the Reseller Panel."
        )
    else:
        await update.message.reply_text("❌ Failed to approve reseller.")
    
    return ConversationHandler.END

async def reseller_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    withdrawals = db.get_pending_reseller_withdrawals()
    
    if not withdrawals:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_reseller_menu")]]
        await query.edit_message_text(
            "💰 **Pending Reseller Withdrawals**\n\nNo pending withdrawals.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    message = "💰 **Pending Reseller Withdrawals**\n\n"
    keyboard = []
    
    for w in withdrawals:
        message += f"**#{w['id']}** - {w.get('first_name', 'User')} (@{w.get('username', 'N/A')})\n"
        message += f"  • Amount: ${w['amount']:.2f}\n"
        message += f"  • Method: {w['payout_method']}\n"
        message += f"  • Margin: {w['margin_percentage']:.1f}%\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✅ Approve #{w['id']}", callback_data=f"approve_res_wd_{w['id']}"),
            InlineKeyboardButton(f"❌ Reject #{w['id']}", callback_data=f"reject_res_wd_{w['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_reseller_menu")])
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def approve_reseller_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    withdrawal_id = int(query.data.split('_')[-1])
    user = update.effective_user
    
    result = db.approve_reseller_withdrawal(withdrawal_id, user.id, notes="Approved by admin")
    
    if result:
        await query.edit_message_text(
            f"✅ **Reseller Withdrawal Approved!**\n\n"
            f"Withdrawal ID: #{withdrawal_id}\n"
            f"Amount: ${result['amount']:.2f}\n\n"
            f"Reseller has been notified."
        )
    else:
        await query.edit_message_text("❌ Failed to approve withdrawal.")

async def reject_reseller_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    withdrawal_id = int(query.data.split('_')[-1])
    user = update.effective_user
    
    result = db.reject_reseller_withdrawal(withdrawal_id, user.id, notes="Rejected by admin")
    
    if result:
        await query.edit_message_text(
            f"❌ **Reseller Withdrawal Rejected**\n\n"
            f"Withdrawal ID: #{withdrawal_id}\n\n"
            f"Reseller has been notified."
        )
    else:
        await query.edit_message_text("❌ Failed to reject withdrawal.")

async def commission_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    top_referrers = db.get_top_buyer_referrers(limit=10)
    current_rate = db.get_saas_referral_commission_rate() * 100
    
    message = f"📊 **Commission Summary**\n\n"
    message += f"🎯 **Current Commission Rate:** {current_rate:.1f}%\n\n"
    message += f"**Top Buyer Referrers:**\n\n"
    
    if top_referrers:
        for idx, ref in enumerate(top_referrers, 1):
            message += f"{idx}. **{ref.get('first_name', 'User')}** (@{ref.get('username', 'N/A')})\n"
            message += f"   • Referrals: {ref['total_referrals']}\n"
            message += f"   • Earned: ${ref['total_earned']:.2f}\n\n"
    else:
        message += "No referral activity yet.\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_reseller_menu")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def cancel_reseller_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action cancelled.")
    return ConversationHandler.END

def get_reseller_management_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("resellermgmt", reseller_management_menu)],
        states={
            APPROVE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, approve_reseller_receive_id)]
        },
        fallbacks=[
            CallbackQueryHandler(reseller_management_menu, pattern="^admin_reseller_menu$"),
            CallbackQueryHandler(view_resellers, pattern="^admin_view_resellers$"),
            CallbackQueryHandler(approve_reseller_start, pattern="^admin_approve_reseller$"),
            CallbackQueryHandler(reseller_withdrawals, pattern="^admin_reseller_withdrawals$"),
            CallbackQueryHandler(commission_summary, pattern="^admin_commission_summary$"),
            CallbackQueryHandler(approve_reseller_withdrawal, pattern="^approve_res_wd_"),
            CallbackQueryHandler(reject_reseller_withdrawal, pattern="^reject_res_wd_"),
            MessageHandler(filters.Regex("^/cancel$"), cancel_reseller_action)
        ]
    )
