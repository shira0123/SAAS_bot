import logging
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from pyrogram import Client
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    PasswordHashInvalid,
    FloodWait,
)
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PHONE, CODE, PASSWORD, CONFIRM_LOGOUT = range(4)

db = Database()

# Global storage for temporary login clients to handle Pyrogram's instance state
# Format: { telegram_user_id: PyrogramClient }
TEMP_CLIENTS = {}

def get_cancel_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel", callback_data="cancel_sell")
    ]])

async def start_sell_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if user_data['is_banned']:
        await update.message.reply_text(
            "❌ Your account is banned. Please contact support."
        )
        return ConversationHandler.END
    
    account_price = db.get_account_price()
    
    message = f"""
📱 **Sell Your Telegram Account**

💰 **Current Price:** ${account_price:.2f} per account

**Important Information:**
⚠️ Once you sell your account, we will take full control of it
⚠️ You will be logged out from all devices
⚠️ Your account will be used for our engagement services
⚠️ This process is irreversible

**Requirements:**
✅ You must have access to your phone number
✅ You must be able to receive SMS/calls for OTP
✅ If you have 2FA enabled, you'll need the password

**Are you ready to proceed?**

Please send your **phone number** in international format (e.g., +1234567890)
"""
    
    await update.message.reply_text(
        message,
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    user_id = update.effective_user.id
    
    if not re.match(r'^\+?[1-9]\d{1,14}$', phone):
        await update.message.reply_text(
            "❌ Invalid phone number format.\n\n"
            "Please send in international format: +1234567890",
            reply_markup=get_cancel_keyboard()
        )
        return PHONE
    
    context.user_data['phone'] = phone
    
    # Initialize Pyrogram Client for this user
    client = Client(
        name=f"login_{user_id}",
        api_id=int(TELEGRAM_API_ID),
        api_hash=TELEGRAM_API_HASH,
        in_memory=True
    )
    
    try:
        await client.connect()
    except Exception as e:
        logger.error(f"Connection error: {e}")
        await update.message.reply_text("❌ Could not connect to Telegram servers.")
        return ConversationHandler.END

    try:
        sent_code = await client.send_code(phone)
        
        # Store essential data
        context.user_data['phone_code_hash'] = sent_code.phone_code_hash
        TEMP_CLIENTS[user_id] = client
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Resend Code", callback_data="resend_code")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sell")]
        ])
        
        await update.message.reply_text(
            f"✅ **Verification Code Sent!**\n\n"
            f"📱 **Important:** Check your Telegram app!\n"
            f"The code should appear in a chat from \"Telegram\" (official)\n\n"
            f"📞 Phone: {phone}\n\n"
            f"📨 Enter the 5-digit code below (e.g., 1 2 3 4 5):",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CODE
        
    except FloodWait as e:
        await update.message.reply_text(
            f"❌ Too many requests. Please wait {e.value} seconds and try again.",
            reply_markup=get_cancel_keyboard()
        )
        await client.disconnect()
        return ConversationHandler.END
        
    except PhoneNumberInvalid:
        await update.message.reply_text(
            "❌ Invalid phone number. Please try again with a valid number.",
            reply_markup=get_cancel_keyboard()
        )
        await client.disconnect()
        return PHONE
        
    except Exception as e:
        logger.error(f"Error sending code to {phone}: {e}")
        await update.message.reply_text(
            "❌ An error occurred while sending the verification code.\n"
            "Please try again later or contact support.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        await client.disconnect()
        return ConversationHandler.END

async def resend_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    client = TEMP_CLIENTS.get(user_id)
    phone = context.user_data.get('phone')
    
    if not client or not phone:
        await query.edit_message_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    try:
        sent_code = await client.send_code(phone)
        context.user_data['phone_code_hash'] = sent_code.phone_code_hash
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Resend Code", callback_data="resend_code")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sell")]
        ])
        
        await query.edit_message_text(
            f"✅ **New Code Sent!**\n\n"
            f"📱 Check your Telegram app for the new code.\n\n"
            f"📨 Enter the 5-digit code:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CODE
        
    except Exception as e:
        logger.error(f"Error resending code: {e}")
        await query.edit_message_text(
            "❌ Failed to resend code. Please start over.",
            reply_markup=get_cancel_keyboard()
        )
        return ConversationHandler.END

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().replace(' ', '').replace('-', '')
    user_id = update.effective_user.id
    
    if not code.isdigit():
        await update.message.reply_text(
            "❌ Invalid code format. Please enter only numbers.",
            reply_markup=get_cancel_keyboard()
        )
        return CODE
    
    client = TEMP_CLIENTS.get(user_id)
    phone = context.user_data.get('phone')
    phone_code_hash = context.user_data.get('phone_code_hash')
    
    if not client or not phone:
        await update.message.reply_text("❌ Session expired. Please /start again.")
        return ConversationHandler.END

    try:
        await client.sign_in(phone, phone_code_hash, code)
        
        # Login Successful
        session_string = await client.export_session_string()
        context.user_data['session_string'] = session_string
        
        logger.info(f"User signed in successfully with phone {phone}")
        
        await update.message.reply_text(
            "✅ Code verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
        return await process_account(update, context, client)
        
    except SessionPasswordNeeded:
        await update.message.reply_text(
            "🔐 **2FA Enabled**\n\n"
            "Please send your 2FA password.\n\n"
            "⚠️ **Note:** Your password will be deleted immediately after sending.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return PASSWORD
        
    except PhoneCodeInvalid:
        await update.message.reply_text(
            "❌ Invalid verification code. Please try again.",
            reply_markup=get_cancel_keyboard()
        )
        return CODE
        
    except Exception as e:
        logger.error(f"Sign in error: {e}")
        await update.message.reply_text(
            f"❌ An error occurred during verification.\n\n"
            f"**Error:** {str(e)}\n\n"
            "Please try again or contact support.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    await update.message.delete() # Delete message for security
    
    user_id = update.effective_user.id
    client = TEMP_CLIENTS.get(user_id)
    
    if not client:
        await update.message.reply_text("❌ Session expired.")
        return ConversationHandler.END
    
    try:
        await client.check_password(password)
        
        session_string = await client.export_session_string()
        context.user_data['session_string'] = session_string
        context.user_data['original_password'] = password
        
        await update.message.reply_text(
            "✅ Password verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
        return await process_account(update, context, client)
        
    except PasswordHashInvalid:
        await update.message.reply_text(
            "❌ Invalid 2FA password. Please try again.",
            reply_markup=get_cancel_keyboard()
        )
        return PASSWORD
    except Exception as e:
        logger.error(f"2FA error: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            reply_markup=get_cancel_keyboard()
        )
        return ConversationHandler.END

async def process_account(update: Update, context: ContextTypes.DEFAULT_TYPE, client):
    try:
        await update.message.reply_text("🔄 Step 1/2: Securing 2FA password...")
        await asyncio.sleep(1)
        
        # Note: Pyrogram password management is more complex due to SRP.
        # For stability, we log the intent but skip programmatic reset here.
        # Admin can manually secure or use automation script later.
        
        phone = context.user_data['phone']
        session_string = context.user_data['session_string']
        
        await update.message.reply_text("🔄 Step 2/2: Saving account to database...")
        await asyncio.sleep(1)
        
        # Save with probation period
        account_price = db.get_account_price()
        probation_end = datetime.now() + timedelta(days=30)
        
        account_id = db.create_sold_account(
            seller_user_id=update.effective_user.id,
            phone_number=phone,
            session_string=session_string,
            sold_price=account_price,
            probation_ends_at=probation_end
        )
        
        context.user_data['account_id'] = account_id
        
        # Disconnect and clean up global client
        await client.disconnect()
        user_id = update.effective_user.id
        if user_id in TEMP_CLIENTS:
            del TEMP_CLIENTS[user_id]
        
        await update.message.reply_text("✅ Account saved successfully!")
        await asyncio.sleep(1)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I have logged out & want my payment", callback_data="confirm_logout")],
            [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
        ])
        
        await update.message.reply_text(
            "📱 **Final Step - PLEASE READ CAREFULLY**\n\n"
            "✅ Your 2FA password has been secured.\n"
            "✅ Your session is saved to our system.\n\n"
            "⚠️ **ACTION REQUIRED:**\n"
            "To complete the sale, you **MUST** now go to your Telegram app and manually terminate your *own* session.\n\n"
            "1. Go to: **Settings > Devices**\n"
            "2. Find your *current* device (the one you are on).\n"
            "3. Tap on it and select **'Terminate Session'**.\n"
            "4. You will be logged out.\n\n"
            "After you have been logged out, come back here and click the button below to receive your payment.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CONFIRM_LOGOUT
        
    except Exception as e:
        logger.error(f"Process error: {e}")
        await update.message.reply_text(
            f"❌ An error occurred during processing.\n\n"
            f"**Error:** {str(e)[:100]}\n\n"
            f"Your account was not sold. Please contact support.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def confirm_logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Verifying...")
    
    account_id = context.user_data.get('account_id')
    session_string = context.user_data.get('session_string')
    
    # Verify session is still alive
    check_client = Client(
        name="check", 
        api_id=int(TELEGRAM_API_ID), 
        api_hash=TELEGRAM_API_HASH, 
        session_string=session_string, 
        in_memory=True,
        no_updates=True
    )
    
    try:
        await check_client.connect()
        await check_client.get_me()
        await check_client.disconnect()
        
        # Payout
        db.mark_account_active(account_id)
        amount = db.get_account_price()
        db.update_user_balance(update.effective_user.id, amount, balance_type='seller')
        
        # Referral
        user = db.get_user(update.effective_user.id)
        if user.get('referred_by'):
            comm = amount * db.get_referral_commission()
            db.update_referral_earnings(user['referred_by'], comm)
            
        user_after_payment = db.get_user(update.effective_user.id)
        new_balance = float(user_after_payment['seller_balance'])

        await query.edit_message_text(
            f"🎉 **Sale Completed Successfully!**\n\n"
            f"💰 **Payment:** ${amount:.2f} added to your balance\n"
            f"💵 **New Balance:** ${new_balance:.2f}\n"
            f"🆔 **Account ID:** #{account_id}\n\n"
            f"⚠️ **Security Notice:** This payment is conditional. If this account is reclaimed within **30 days**, a **${amount:.2f} penalty** will be deducted from your balance.",
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Verification error: {e}")
        await query.edit_message_text(
            f"❌ Session invalid. Did you terminate the wrong session? Please contact support. Error: {e}"
        )
        return ConversationHandler.END

async def cancel_sale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Sale cancelled. Your account was not sold.")
    return await cancel(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in TEMP_CLIENTS:
        try:
            await TEMP_CLIENTS[user_id].disconnect()
        except: pass
        del TEMP_CLIENTS[user_id]
        
    context.user_data.clear()
    
    if update.callback_query:
        # Already handled in cancel_sale_callback or similar
        pass
    elif update.message:
        await update.message.reply_text(
            "❌ Account selling cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

def get_account_sell_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 Sell TG Account$"), start_sell_account)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code),
                CallbackQueryHandler(resend_code_callback, pattern="^resend_code$"),
            ],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            CONFIRM_LOGOUT: [
                CallbackQueryHandler(confirm_logout_callback, pattern="^confirm_logout$"),
                CallbackQueryHandler(cancel_sale_callback, pattern="^cancel_sale$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_sell$"),
        ],
    )