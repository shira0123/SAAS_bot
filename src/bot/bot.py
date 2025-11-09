import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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
from src.database.config import BOT_TOKEN, MIN_WITHDRAWAL
import random
import string

import src.seller.seller_profile as seller_profile
import src.seller.seller_withdrawals as seller_withdrawals
import src.admin.admin_controls as admin_controls
import src.admin.admin_reporting as admin_reporting
import src.buyer.buyer_menu as buyer_menu
import src.utils.account_pool_manager as account_pool_manager
import src.admin.admin_rate_management as admin_rate_management
import src.buyer.buy_plan as buy_plan
import src.buyer.deposit_menu as deposit_menu
import src.admin.promo_code_management as promo_code_management
import src.admin.admin_deposit_management as admin_deposit_management
import src.buyer.plan_management as plan_management
import src.admin.saas_admin_reports as saas_admin_reports
import src.bot.notification_system as notification_system
import src.admin.broadcast_admin as broadcast_admin
import src.admin.admin_reseller_management as admin_reseller_management

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_seller_menu():
    keyboard = [
        [KeyboardButton("💰 Sell TG Account"), KeyboardButton("💎 Buyer Menu")],
        [KeyboardButton("💸 Withdraw"), KeyboardButton("👤 Profile")],
        [KeyboardButton("🎁 Refer & Earn"), KeyboardButton("💬 Support")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    keyboard = [
        [KeyboardButton("📊 Statistics"), KeyboardButton("👥 Users")],
        [KeyboardButton("💳 Withdrawals"), KeyboardButton("📱 Accounts")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("🔙 Back to User Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    existing_user = db.get_user(user.id)
    
    if not existing_user:
        referral_code = generate_referral_code()
        while db.get_user_by_referral(referral_code):
            referral_code = generate_referral_code()
        
        referred_by = None
        if context.args and len(context.args) > 0:
            ref_code = context.args[0]
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
        
        account_price = db.get_account_price()
        welcome_message = f"""
🎉 Welcome to the Account Marketplace Bot!

👋 Hello {user.first_name}!

You can earn money by selling your Telegram accounts to our platform.

💰 **Current Rate:** ${account_price:.2f} per account
💸 **Minimum Withdrawal:** ${MIN_WITHDRAWAL}
🎁 **Referral Bonus:** Earn commission for every friend you invite!

Choose an option from the menu below to get started:
"""
    else:
        is_admin = db.is_admin(user.id)
        welcome_message = f"""
👋 Welcome back, {user.first_name}!

💰 **Seller Balance:** ${existing_user['seller_balance']:.2f}
💳 **Buyer Balance:** ${existing_user['buyer_wallet_balance']:.2f}

Choose an option from the menu below:
"""
        if is_admin:
            welcome_message += "\n🔑 **Admin Access Granted**"
    
    is_admin = db.is_admin(user.id)
    menu = get_admin_menu() if is_admin else get_seller_menu()
    
    await update.message.reply_text(welcome_message, reply_markup=menu)

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    referral_count = db.get_referral_count(user.id)
    
    message = f"""
🎁 **Refer & Earn**

Invite your friends and earn commission on their earnings!

**Your Referral Link:**
`t.me/{context.bot.username}?start={user_data['referral_code']}`

**Your Stats:**
• Total Referrals: {referral_count}
• Referral Earnings: ${user_data['referral_earnings']:.2f}

**How it works:**
1. Share your referral link
2. When someone signs up using your link
3. You earn a percentage of their account sales!

💡 The more people you refer, the more you earn!
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """
💬 **Support**

Need help? We're here for you!

**Common Questions:**
• How long does verification take? Usually instant!
• When will I receive payment? After successful account verification
• How do withdrawals work? Request via the Withdraw button

**Contact Admin:**
For any issues, questions, or concerns, please contact our support team.

**Business Hours:**
Monday - Sunday: 9 AM - 11 PM (UTC)

We typically respond within a few hours!
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only available to admins.")
        return
    
    if not context.args or len(context.args) != 1:
        current_price = db.get_account_price()
        await update.message.reply_text(
            f"💰 **Current Account Price:** ${current_price:.2f}\n\n"
            "**Usage:** /setprice <amount>\n"
            "**Example:** /setprice 15.00",
            parse_mode='Markdown'
        )
        return
    
    try:
        new_price = float(context.args[0])
        if new_price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0")
            return
        
        db.set_account_price(new_price)
        await update.message.reply_text(
            f"✅ **Account Price Updated!**\n\n"
            f"New price: ${new_price:.2f} per account\n\n"
            "This will apply to all new account sales.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid price format. Please use a number (e.g., 15.00)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "👤 Profile":
        await seller_profile.show_profile(update, context)
    elif text == "🎁 Refer & Earn":
        await handle_referral(update, context)
    elif text == "💬 Support":
        await handle_support(update, context)
    elif text == "💎 Buyer Menu":
        await buyer_menu.show_buyer_menu(update, context)
    elif text == "💎 Buy Plan":
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
    elif text == "🔙 Back to Seller Menu":
        await update.message.reply_text("🔙 Switched to Seller Menu", reply_markup=get_seller_menu())
    elif text == "🔙 Back to Menu":
        await update.message.reply_text(
            "📱 Main Menu",
            reply_markup=get_seller_menu()
        )
    elif text == "🔙 Back to User Menu":
        if db.is_admin(update.effective_user.id):
            await update.message.reply_text("Switching to user menu...", reply_markup=get_seller_menu())
    elif text == "⚙️ Settings":
        if db.is_admin(update.effective_user.id):
            await admin_rate_management.show_rate_management(update, context)
        else:
            await update.message.reply_text("⛔ Admin access required")
    else:
        is_admin = db.is_admin(update.effective_user.id)
        if is_admin and text in ["📊 Statistics", "👥 Users", "💳 Withdrawals", "📱 Accounts"]:
            await update.message.reply_text(f"Admin feature '{text}' - Coming soon in future phases!")
        elif text not in ["💰 Sell TG Account", "💸 Withdraw", "💳 Set Payout Info"]:
            await update.message.reply_text("Please use the menu buttons below to navigate.")

def main():
    try:
        db.init_schema()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    from src.seller.account_seller import get_account_sell_handler
    
    payout_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 Set Payout Info$"), seller_profile.start_set_payout)],
        states={
            seller_profile.PAYOUT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_profile.receive_payout_method)],
            seller_profile.PAYOUT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_profile.receive_payout_details)],
        },
        fallbacks=[CommandHandler("cancel", seller_profile.cancel_payout_setup)],
    )
    
    withdraw_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), seller_withdrawals.start_withdraw)],
        states={
            seller_withdrawals.REQUEST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, seller_withdrawals.receive_amount)],
        },
        fallbacks=[CommandHandler("cancel", seller_withdrawals.cancel_withdraw)],
    )
    
    application.add_handler(get_account_sell_handler())
    application.add_handler(payout_handler)
    application.add_handler(withdraw_handler)
    
    add_account_handler = ConversationHandler(
        entry_points=[CommandHandler("addaccount", account_pool_manager.start_add_account)],
        states={
            account_pool_manager.ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_pool_manager.receive_add_phone)],
            account_pool_manager.ADD_SESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_pool_manager.receive_add_session)],
        },
        fallbacks=[CommandHandler("cancel", account_pool_manager.cancel_add_account)],
    )
    
    application.add_handler(add_account_handler)
    
    application.add_handler(buy_plan.get_buy_plan_handler())
    application.add_handler(admin_rate_management.get_rate_management_handler())
    application.add_handler(deposit_menu.get_deposit_handler())
    application.add_handler(promo_code_management.get_promo_management_handler())
    application.add_handler(plan_management.get_plan_management_handler())
    
    import src.buyer.buyer_referral_program as buyer_referral_program
    import src.buyer.buyer_referral_withdrawals as buyer_referral_withdrawals
    import src.admin.admin_reseller_management as admin_reseller_management
    import src.buyer.reseller_panel as reseller_panel
    
    application.add_handler(buyer_referral_program.get_buyer_referral_handler())
    application.add_handler(buyer_referral_withdrawals.get_buyer_referral_withdrawal_handler())
    application.add_handler(admin_reseller_management.get_reseller_management_handler())
    application.add_handler(reseller_panel.get_reseller_panel_handler())
    
    application.add_handler(MessageHandler(filters.Regex("^📊 My Referrals$"), buyer_referral_program.show_my_referrals))
    application.add_handler(MessageHandler(filters.Regex("^💵 Referral Earnings$"), buyer_referral_program.show_my_referrals))
    application.add_handler(MessageHandler(filters.Regex("^💼 Create Plan Link$"), reseller_panel.create_plan_link))
    application.add_handler(MessageHandler(filters.Regex("^📊 My Sales$"), reseller_panel.show_sales))
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setprice", setprice))
    application.add_handler(CommandHandler("setref", admin_reporting.setref_command))
    application.add_handler(CommandHandler("accsell", admin_reporting.accsell_command))
    application.add_handler(CommandHandler("alluser", admin_reporting.alluser_command))
    application.add_handler(CommandHandler("stats", admin_reporting.stats_command))
    application.add_handler(CommandHandler("accounts", account_pool_manager.accounts_command))
    application.add_handler(CommandHandler("removeaccount", account_pool_manager.remove_account_command))
    application.add_handler(CommandHandler("withdraws", admin_controls.list_pending_withdrawals))
    application.add_handler(CommandHandler("withdrawlimit", admin_controls.set_withdrawal_limits))
    application.add_handler(CommandHandler("ban", admin_controls.ban_user_command))
    application.add_handler(CommandHandler("unban", admin_controls.unban_user_command))
    application.add_handler(CommandHandler("stopwithdraw", admin_controls.stop_withdraw_command))
    application.add_handler(CommandHandler("allowwithdraw", admin_controls.allow_withdraw_command))
    application.add_handler(CommandHandler("verifydep", admin_deposit_management.verify_deposit_command))
    application.add_handler(CommandHandler("deposits", admin_deposit_management.view_pending_deposits))
    application.add_handler(CommandHandler("promo", promo_code_management.show_promo_management))
    application.add_handler(CommandHandler("saasreports", saas_admin_reports.show_saas_reports_menu))
    application.add_handler(CommandHandler("broadcast", broadcast_admin.show_broadcast_menu))
    application.add_handler(CommandHandler("adminmgmt", broadcast_admin.show_admin_management_menu))
    application.add_handler(CommandHandler("resellermgmt", admin_reseller_management.reseller_management_menu))
    
    application.add_handler(broadcast_admin.get_broadcast_handler())
    application.add_handler(broadcast_admin.get_admin_management_handler())
    
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_saas_reports_menu, pattern="^saas_reports$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_payment_reports, pattern="^saas_payments$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_payment_details, pattern="^payments_"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_revenue_summary, pattern="^payments_summary$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_sales_stats, pattern="^saas_sales$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.show_export_menu, pattern="^saas_export$"))
    application.add_handler(CallbackQueryHandler(saas_admin_reports.export_csv_data, pattern="^export_"))
    
    application.add_handler(CallbackQueryHandler(broadcast_admin.show_admin_management_menu, pattern="^admin_manage$"))
    application.add_handler(CallbackQueryHandler(broadcast_admin.view_admins, pattern="^admin_view$"))
    application.add_handler(CallbackQueryHandler(broadcast_admin.view_admin_logs, pattern="^admin_logs$"))
    
    application.add_handler(CallbackQueryHandler(admin_controls.view_withdrawal_detail, pattern="^withdrawal_view_"))
    application.add_handler(CallbackQueryHandler(admin_controls.approve_withdrawal, pattern="^withdrawal_approve_"))
    application.add_handler(CallbackQueryHandler(admin_controls.reject_withdrawal, pattern="^withdrawal_reject_"))
    application.add_handler(CallbackQueryHandler(admin_controls.back_to_withdrawal_list, pattern="^withdrawal_back$"))
    
    application.add_handler(CallbackQueryHandler(admin_rate_management.show_rate_management, pattern="^show_rates$"))
    application.add_handler(CallbackQueryHandler(buy_plan.show_plan_types, pattern="^buyer_back$"))
    
    application.add_handler(CallbackQueryHandler(plan_management.view_plan_details, pattern="^plan_view_"))
    application.add_handler(CallbackQueryHandler(plan_management.renew_plan, pattern="^plan_renew_"))
    application.add_handler(CallbackQueryHandler(plan_management.cancel_plan, pattern="^plan_cancel_"))
    application.add_handler(CallbackQueryHandler(plan_management.confirm_cancel_plan, pattern="^confirm_cancel_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
