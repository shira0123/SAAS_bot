import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

DEPOSIT_METHOD, UPI_UTR, PROMO_CODE_INPUT = range(3)

async def show_deposit_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deposit method options"""
    keyboard = [
        [InlineKeyboardButton("💳 UPI Payment", callback_data="deposit_upi")],
        [InlineKeyboardButton("💰 Paytm", callback_data="deposit_paytm")],
        [InlineKeyboardButton("₿ Crypto (CryptoMus)", callback_data="deposit_crypto")],
        [InlineKeyboardButton("🔶 Binance", callback_data="deposit_binance")],
        [InlineKeyboardButton("🎁 Apply Promo Code", callback_data="deposit_promo")],
        [InlineKeyboardButton("🔙 Back to Buyer Menu", callback_data="buyer_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = db.get_user(update.effective_user.id)
    current_balance = user.get('buyer_wallet_balance', 0.00) if user else 0.00
    
    message = f"""
💰 **Deposit Funds to Wallet**

**Current Wallet Balance:** ${current_balance:.2f}

Choose a payment method to add funds:

**💳 UPI Payment** - Quick deposit via UPI
**💰 Paytm** - Automated Paytm gateway
**₿ Crypto** - Pay with cryptocurrency
**🔶 Binance** - Binance Pay

**🎁 Apply Promo Code** - Get bonus credits

Select an option below:
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
    
    return DEPOSIT_METHOD

async def handle_upi_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UPI deposit - manual verification flow"""
    query = update.callback_query
    await query.answer()
    
    upi_id = os.getenv('UPI_ID', 'merchant@upi')
    
    message = f"""
💳 **UPI Payment Method**

**Step 1:** Send payment to our UPI ID
**UPI ID:** `{upi_id}`

**Step 2:** After payment, send us the **UTR Number** (Transaction Reference)

You can find the UTR number in your payment confirmation message.

**Format:** 12-digit number (e.g., 123456789012)

Please send the UTR number to proceed:
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    return UPI_UTR

async def receive_upi_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate UTR number"""
    utr = update.message.text.strip()
    
    if not utr.isdigit() or len(utr) != 12:
        await update.message.reply_text(
            "❌ Invalid UTR format. Please send a valid 12-digit UTR number:"
        )
        return UPI_UTR
    
    user_id = update.effective_user.id
    
    db.create_deposit_request(
        user_id=user_id,
        amount=0.00,
        payment_method='UPI',
        transaction_id=utr,
        status='pending_verification'
    )
    
    admins = db.get_all_admins()
    admin_ids = [admin['user_id'] for admin in admins if admin.get('is_active')]
    
    user = db.get_user(user_id)
    username = user.get('username', 'N/A') if user else 'N/A'
    
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"""
🔔 **New UPI Deposit Request**

**User ID:** {user_id}
**Username:** @{username}
**Payment Method:** UPI
**UTR Number:** `{utr}`
**Status:** Pending Verification

Please verify the transaction and update the deposit amount using:
/verifydep {utr} <amount>
""",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    await update.message.reply_text(
        "✅ **UTR Received!**\n\n"
        f"**Transaction ID:** `{utr}`\n"
        f"**Status:** Pending Verification\n\n"
        "Our team will verify your payment shortly and credit your wallet.\n"
        "You'll receive a confirmation once verified.\n\n"
        "Thank you for your patience! ⏳",
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_paytm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Paytm automated gateway"""
    query = update.callback_query
    await query.answer()
    
    message = """
💰 **Paytm Payment Gateway**

**Coming Soon!**

This payment method is under integration.

Please use UPI or other available methods for now.
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_crypto_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CryptoMus cryptocurrency payment"""
    query = update.callback_query
    await query.answer()
    
    message = """
₿ **Cryptocurrency Payment (CryptoMus)**

**Coming Soon!**

Crypto payment integration is under development.

Please use UPI or other available methods for now.
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_binance_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Binance Pay"""
    query = update.callback_query
    await query.answer()
    
    message = """
🔶 **Binance Pay**

**Coming Soon!**

Binance Pay integration is under development.

Please use UPI or other available methods for now.
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def handle_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle promo code application"""
    query = update.callback_query
    await query.answer()
    
    message = """
🎁 **Apply Promo Code**

Enter your promo code to receive bonus credits.

**Format:** Your promo code (e.g., WELCOME10, BONUS50)

Please send the promo code:
"""
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown'
    )
    
    return PROMO_CODE_INPUT

async def receive_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate promo code"""
    promo_code = update.message.text.strip().upper()
    user_id = update.effective_user.id
    
    result = db.apply_promo_code(user_id, promo_code)
    
    if result['success']:
        await update.message.reply_text(
            f"✅ **Promo Code Applied Successfully!**\n\n"
            f"**Code:** {promo_code}\n"
            f"**Bonus Amount:** ${result['bonus_amount']:.2f}\n"
            f"**New Wallet Balance:** ${result['new_balance']:.2f}\n\n"
            f"Congratulations! 🎉",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ **Promo Code Error**\n\n"
            f"{result['error']}\n\n"
            f"Please check the code and try again.",
            parse_mode='Markdown'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel deposit process"""
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ **Deposit Cancelled**\n\n"
        "You can try again anytime from the Deposit menu."
    )
    
    return ConversationHandler.END

def get_deposit_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_upi_deposit, pattern='^deposit_upi$'),
            CallbackQueryHandler(handle_paytm_deposit, pattern='^deposit_paytm$'),
            CallbackQueryHandler(handle_crypto_deposit, pattern='^deposit_crypto$'),
            CallbackQueryHandler(handle_binance_deposit, pattern='^deposit_binance$'),
            CallbackQueryHandler(handle_promo_code, pattern='^deposit_promo$')
        ],
        states={
            UPI_UTR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_upi_utr)
            ],
            PROMO_CODE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_code)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_deposit)
        ],
        name="deposit",
        persistent=False,
        per_message=False
    )
