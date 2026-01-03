import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from src.database.database import Database
from src.database.config import BUYER_BOT_TOKEN, ADMIN_IDS

import src.buyer.buyer_menu as buyer_menu
import src.buyer.buy_plan as buy_plan
import src.buyer.deposit_menu as deposit_menu
import src.buyer.plan_management as plan_management
import src.buyer.buyer_referral_program as buyer_referral_program
import src.buyer.buyer_referral_withdrawals as buyer_referral_withdrawals
import src.buyer.reseller_panel as reseller_panel

import src.admin.admin_rate_management as admin_rate_management
import src.admin.promo_code_management as promo_code_management
import src.admin.admin_deposit_management as admin_deposit_management
import src.admin.saas_admin_reports as saas_admin_reports
import src.admin.broadcast_admin as broadcast_admin
import src.admin.admin_reseller_management as admin_reseller_management
import src.utils.account_pool_manager as account_pool_manager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

def generate_referral_code(length=8):
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_admin_menu():
    """Returns the ReplyKeyboardMarkup for the admin menu."""
    keyboard = [
        [KeyboardButton("📊 SaaS Reports"), KeyboardButton("📱 Accounts")],
        [KeyboardButton("🎁 Promo Codes"), KeyboardButton("💰 Deposits")],
        [KeyboardButton("👔 Resellers"), KeyboardButton("⚙️ Rates")],
        [KeyboardButton("📢 Broadcast"), KeyboardButton("👑 Admin Mgmt")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def admin_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles 'Back' buttons in admin menus."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔑 **Admin Menu**\n\nWelcome back. Select an option:",
        reply_markup=get_admin_menu()
    )

async def buyer_support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Support' button."""
    message = """
💬 **Support**

Need help with your plans or deposits? We're here for you!

**Common Questions:**
• How long does plan activation take? Instant, after payment.
• How does Drip-Feed work? We spread your order over the hours you select.

**Contact Admin:**
For any issues, please contact our support team.
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    existing_user = db.get_user(user.id)
    
    if not existing_user:
        referral_code = generate_referral_code()
        while db.get_user_by_referral(referral_code):
            referral_code = generate_referral_code()
        
        referred_by = None
        if context.args and len(context.args) > 0:
            ref_code = context.args[0]
            if ref_code.startswith('buyref_'):
                ref_code = ref_code.replace('buyref_', '')
            referrer = db.get_user_by_referral(ref_code)
            if referrer:
                referred_by = referrer['user_id']
        
        db.create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referral_code=referral_code,
            referred_by=referred_by
        )
    
    is_admin = db.is_admin(user.id)
    if is_admin:
        await update.message.reply_text(
            f"🔑 **Admin Access**\n\nWelcome, {user.first_name}!",
            reply_markup=get_admin_menu()
        )
    else:
        await buyer_menu.show_buyer_menu(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages and menu buttons."""
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if user is admin for routing
    is_admin = db.is_admin(user_id)
    
    if is_admin:
        if text == "📊 SaaS Reports":
            await saas_admin_reports.show_saas_reports_menu(update, context)
            return
        elif text == "📱 Accounts":
            await account_pool_manager.accounts_command(update, context)
            return
        elif text == "🎁 Promo Codes":
            await promo_code_management.show_promo_management(update, context)
            return
        elif text == "💰 Deposits":
            await admin_deposit_management.view_pending_deposits(update, context)
            return
        elif text == "👔 Resellers":
            await admin_reseller_management.reseller_management_menu(update, context)
            return
        elif text == "⚙️ Rates":
            await admin_rate_management.show_rate_management(update, context)
            return
        elif text == "📢 Broadcast":
            await broadcast_admin.show_broadcast_menu(update, context)
            return
        elif text == "👑 Admin Mgmt":
            await broadcast_admin.show_admin_management_menu(update, context)
            return

    # Buyer Menu Logic
    if text == "💎 Buy Plan":
        await buyer_menu.buy_plan(update, context)
    elif text == "💰 Deposit":
        await buyer_menu.deposit(update, context)
    elif text == "📋 My Plans":
        await plan_management.show_my_plans(update, context)
    elif text == "📊 Plan History":
        await plan_management.show_plan_history(update, context)
    elif text == "🎁 Referral Program":
        await buyer_menu.buyer_referral(update, context)
    elif text == "👔 Reseller Panel":
        await buyer_menu.reseller_panel(update, context)
    elif text == "💬 Support":
        await buyer_support_handler(update, context)
    elif text == "🔙 Back to Buyer Menu":
        await buyer_menu.show_buyer_menu(update, context)
    else:
        await update.message.reply_text("Please use the menu buttons or /start.")

def main():
    """Starts the Buyer Bot."""
    # Ensure database schema is ready before any workers start
    try:
        db.init_schema()
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    if not BUYER_BOT_TOKEN:
        logger.error("BUYER_BOT_TOKEN not found!")
        return
    
    application = Application.builder().token(BUYER_BOT_TOKEN).build()

    # --- Conversation Handlers ---
    application.add_handler(buy_plan.get_buy_plan_handler())
    application.add_handler(admin_rate_management.get_rate_management_handler())
    application.add_handler(deposit_menu.get_deposit_handler())
    application.add_handler(promo_code_management.get_promo_management_handler())
    application.add_handler(plan_management.get_plan_management_handler())
    application.add_handler(buyer_referral_program.get_buyer_referral_handler())
    application.add_handler(buyer_referral_withdrawals.get_buyer_referral_withdrawal_handler())
    application.add_handler(admin_reseller_management.get_reseller_management_handler())
    application.add_handler(reseller_panel.get_reseller_panel_handler())
    application.add_handler(broadcast_admin.get_broadcast_handler())
    application.add_handler(broadcast_admin.get_admin_management_handler())
    
    add_account_handler = ConversationHandler(
        entry_points=[CommandHandler("addaccount", account_pool_manager.start_add_account)],
        states={
            account_pool_manager.ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_pool_manager.receive_add_phone)],
            account_pool_manager.ADD_SESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_pool_manager.receive_add_session)],
        },
        fallbacks=[CommandHandler("cancel", account_pool_manager.cancel_add_account)],
    )
    application.add_handler(add_account_handler)

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("accounts", account_pool_manager.accounts_command))
    application.add_handler(CommandHandler("removeaccount", account_pool_manager.remove_account_command))
    application.add_handler(CommandHandler("verifydep", admin_deposit_management.verify_deposit_command))
    application.add_handler(CommandHandler("deposits", admin_deposit_management.view_pending_deposits))
    application.add_handler(CommandHandler("promo", promo_code_management.show_promo_management))
    application.add_handler(CommandHandler("saasreports", saas_admin_reports.show_saas_reports_menu))
    application.add_handler(CommandHandler("broadcast", broadcast_admin.show_broadcast_menu))
    application.add_handler(CommandHandler("adminmgmt", broadcast_admin.show_admin_management_menu))
    application.add_handler(CommandHandler("resellermgmt", admin_reseller_management.reseller_management_menu))

    # --- Callback Handlers ---
    application.add_handler(CallbackQueryHandler(admin_back_handler, pattern="^admin_back_from_rates$"))
    application.add_handler(CallbackQueryHandler(admin_back_handler, pattern="^admin_back$"))
    
    # SaaS Report Callbacks
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_saas_reports_menu, pattern="^saas_reports$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_payment_reports, pattern="^saas_payments$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_payment_details, pattern="^payments_"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_revenue_summary, pattern="^payments_summary$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_sales_stats, pattern="^saas_sales$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_export_menu, pattern="^saas_export$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.export_csv_data, pattern="^export_"))
    
    # Admin Manage Callbacks
    application.add_handler(CallbackQueryHandler(broadcast_admin.show_admin_management_menu, pattern="^admin_manage$"))
    application.add_handler(CallbackQueryHandler(broadcast_admin.view_admins, pattern="^admin_view$"))
    application.add_handler(CallbackQueryHandler(broadcast_admin.view_admin_logs, pattern="^admin_logs$"))
    
    # Plan Management Callbacks
    application.add_handler(CallbackQueryHandler(admin_rate_management.show_rate_management, pattern="^show_rates$"))
    application.add_handler(CallbackQueryHandler(buyer_menu.show_buyer_menu, pattern="^buyer_back$"))
    application.add_handler(CallbackQueryHandler(plan_management.back_to_plans, pattern="^plans_back$"))
    application.add_handler(CallbackQueryHandler(plan_management.view_plan_details, pattern="^plan_view_"))
    
    # CRITICAL: Unique patterns for plan termination to avoid 'Duration' prompt conflict
    application.add_handler(CallbackQueryHandler(plan_management.renew_plan, pattern="^plan_renew_"))
    application.add_handler(CallbackQueryHandler(plan_management.cancel_plan, pattern="^plan_cancel_"))
    application.add_handler(CallbackQueryHandler(plan_management.confirm_cancel_plan, pattern="^conf_term_")) # Matches updated plan_management pattern
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Buyer Bot (Bot 2) started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()