import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    PasswordHashInvalidError,
)
from telethon.sessions import StringSession
from database import Database
from config import TELEGRAM_API_ID, TELEGRAM_API_HASH
import re

logger = logging.getLogger(__name__)

PHONE, CODE, PASSWORD, CONFIRM_LOGOUT = range(4)

db = Database()

async def start_sell_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    if user_data['is_banned']:
        await update.message.reply_text(
            "❌ Your account is banned. Please contact support.",
            reply_markup=get_main_menu()
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

Or send /cancel to stop this process.
"""
    
    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardRemove()
    )
    return PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    
    if not re.match(r'^\+?[1-9]\d{1,14}$', phone):
        await update.message.reply_text(
            "❌ Invalid phone number format.\n\n"
            "Please send in international format: +1234567890\n"
            "Or /cancel to stop."
        )
        return PHONE
    
    context.user_data['phone'] = phone
    context.user_data['client'] = None
    
    try:
        client = TelegramClient(
            StringSession(),
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH
        )
        
        await client.connect()
        
        result = await client.send_code_request(phone)
        context.user_data['phone_code_hash'] = result.phone_code_hash
        context.user_data['client'] = client
        
        await update.message.reply_text(
            f"✅ Verification code sent to **{phone}**\n\n"
            "📨 Please enter the code you received (e.g., 12345)\n\n"
            "Or /cancel to stop.",
            parse_mode='Markdown'
        )
        return CODE
        
    except PhoneNumberInvalidError:
        await update.message.reply_text(
            "❌ Invalid phone number. Please try again with a valid number.\n"
            "Or /cancel to stop."
        )
        return PHONE
    except Exception as e:
        logger.error(f"Error sending code: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again later or contact support.\n"
            "/cancel to stop."
        )
        return ConversationHandler.END

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().replace('-', '').replace(' ', '')
    
    if not code.isdigit():
        await update.message.reply_text(
            "❌ Invalid code format. Please enter only numbers.\n"
            "Or /cancel to stop."
        )
        return CODE
    
    client = context.user_data.get('client')
    phone = context.user_data.get('phone')
    
    if not client or not phone:
        await update.message.reply_text(
            "❌ Session expired. Please start over with /sell"
        )
        return ConversationHandler.END
    
    try:
        await client.sign_in(phone, code)
        
        session_string = client.session.save()
        context.user_data['session_string'] = session_string
        
        await update.message.reply_text(
            "✅ Code verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
        result = await process_account(update, context)
        return result
        
    except SessionPasswordNeededError:
        await update.message.reply_text(
            "🔐 **2FA Enabled**\n\n"
            "Your account has Two-Factor Authentication enabled.\n"
            "Please send your 2FA password.\n\n"
            "Or /cancel to stop.",
            parse_mode='Markdown'
        )
        context.user_data['needs_2fa'] = True
        return PASSWORD
        
    except PhoneCodeInvalidError:
        await update.message.reply_text(
            "❌ Invalid verification code. Please try again.\n"
            "Or /cancel to stop."
        )
        return CODE
        
    except Exception as e:
        logger.error(f"Error during sign in: {e}")
        await update.message.reply_text(
            "❌ An error occurred during verification. Please try again.\n"
            "/cancel to stop."
        )
        return ConversationHandler.END

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    
    await update.message.delete()
    
    client = context.user_data.get('client')
    
    if not client:
        await update.message.reply_text(
            "❌ Session expired. Please start over with /sell"
        )
        return ConversationHandler.END
    
    try:
        await client.sign_in(password=password)
        
        session_string = client.session.save()
        context.user_data['session_string'] = session_string
        
        await update.message.reply_text(
            "✅ Password verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
        result = await process_account(update, context)
        return result
        
    except PasswordHashInvalidError:
        await update.message.reply_text(
            "❌ Invalid 2FA password. Please try again.\n"
            "Or /cancel to stop."
        )
        return PASSWORD
        
    except Exception as e:
        logger.error(f"Error with 2FA: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.\n"
            "/cancel to stop."
        )
        return ConversationHandler.END

async def process_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('client')
    phone = context.user_data.get('phone')
    session_string = context.user_data.get('session_string')
    
    try:
        await update.message.reply_text("🔄 Step 1/3: Terminating other sessions...")
        await asyncio.sleep(1)
        
        authorizations = await client.get_authorizations()
        for auth in authorizations:
            if not auth.current:
                try:
                    await auth.terminate()
                except:
                    pass
        
        await update.message.reply_text("✅ Other sessions terminated")
        await asyncio.sleep(1)
        
        await update.message.reply_text("🔄 Step 2/3: Setting up 2FA security...")
        await asyncio.sleep(1)
        
        try:
            await client.edit_2fa(new_password='5000')
            await update.message.reply_text("✅ Security configured")
        except Exception as e:
            logger.warning(f"2FA setup warning: {e}")
            await update.message.reply_text("⚠️ Security configuration skipped")
        
        await asyncio.sleep(1)
        
        await update.message.reply_text("🔄 Step 3/3: Saving account to database...")
        await asyncio.sleep(1)
        
        account_id = db.create_sold_account(
            seller_user_id=update.effective_user.id,
            phone_number=phone,
            session_string=session_string
        )
        
        context.user_data['account_id'] = account_id
        
        await update.message.reply_text("✅ Account saved successfully!")
        await asyncio.sleep(1)
        
        keyboard = [[KeyboardButton("✅ I Have Logged Out")]]
        await update.message.reply_text(
            "📱 **Final Step**\n\n"
            "You should now be logged out from all your devices.\n\n"
            "Please check your Telegram app and confirm you have been logged out.\n\n"
            "Once confirmed, press the button below to complete the sale and receive payment.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
            parse_mode='Markdown'
        )
        
        return CONFIRM_LOGOUT
        
    except Exception as e:
        logger.error(f"Error processing account: {e}")
        await update.message.reply_text(
            "❌ An error occurred during processing. Your account was not sold.\n"
            "Please contact support if this persists."
        )
        return ConversationHandler.END
    finally:
        if client and client.is_connected():
            await client.disconnect()

async def confirm_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text != "✅ I Have Logged Out":
        await update.message.reply_text(
            "Please press the '✅ I Have Logged Out' button to confirm."
        )
        return CONFIRM_LOGOUT
    
    account_id = context.user_data.get('account_id')
    phone = context.user_data.get('phone')
    session_string = context.user_data.get('session_string')
    
    if not account_id or not session_string:
        await update.message.reply_text(
            "❌ Error: Account data missing. The selling process may have failed.\n"
            "Please contact support with this error."
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    try:
        await update.message.reply_text("🔍 Verifying logout status...")
        
        verify_client = TelegramClient(
            StringSession(session_string),
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH
        )
        
        await verify_client.connect()
        
        if not await verify_client.is_user_authorized():
            await update.message.reply_text(
                "❌ Verification failed. Session appears invalid.\n"
                "Please contact support."
            )
            await verify_client.disconnect()
            return ConversationHandler.END
        
        authorizations = await verify_client.get_authorizations()
        active_sessions = len([a for a in authorizations if not a.current])
        
        await verify_client.disconnect()
        
        if active_sessions > 0:
            await update.message.reply_text(
                f"⚠️ Warning: {active_sessions} other session(s) still active.\n\n"
                "We have taken control of your account, but you may still be logged in elsewhere.\n"
                "Please manually log out from all devices for security.\n\n"
                "Processing payment..."
            )
        
        account_price = db.get_account_price()
        db.update_user_balance(update.effective_user.id, account_price, 'seller')
        
        db.mark_account_active(account_id)
        
        referred_by = db.get_user(update.effective_user.id).get('referred_by')
        if referred_by:
            from config import REFERRAL_COMMISSION
            commission = account_price * REFERRAL_COMMISSION
            db.update_referral_earnings(referred_by, commission)
        
        user_data = db.get_user(update.effective_user.id)
        
        success_message = f"""
🎉 **Account Sold Successfully!**

💰 **Payout:** ${account_price:.2f}
📱 **Account ID:** #{account_id}
📞 **Phone:** {phone}

💵 **Your New Balance:** ${user_data['seller_balance']:.2f}

You can withdraw your earnings anytime using the Withdraw button!

Thank you for selling your account! 🙏
"""
        
        await update.message.reply_text(
            success_message,
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        await update.message.reply_text(
            "❌ Verification failed. Please contact support.\n"
            f"Account ID: #{account_id}"
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('client')
    if client and client.is_connected():
        await client.disconnect()
    
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Account selling process cancelled.\n\n"
        "You can start again anytime using the 'Sell TG Account' button.",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

def get_main_menu():
    from bot import get_seller_menu
    return get_seller_menu()

def get_account_sell_handler():
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^💰 Sell TG Account$'), start_sell_account),
            CommandHandler('sell', start_sell_account)
        ],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            CONFIRM_LOGOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_logout)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="account_selling",
        persistent=False
    )
