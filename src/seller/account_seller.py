import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telethon import TelegramClient, functions
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    PasswordHashInvalidError,
    FloodWaitError,
)
from telethon.sessions import StringSession
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PHONE, CODE, PASSWORD, CONFIRM_LOGOUT = range(4)

db = Database()

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
    
    if not re.match(r'^\+?[1-9]\d{1,14}$', phone):
        await update.message.reply_text(
            "❌ Invalid phone number format.\n\n"
            "Please send in international format: +1234567890",
            reply_markup=get_cancel_keyboard()
        )
        return PHONE
    
    context.user_data['phone'] = phone
    
    client = None
    try:
        api_id = int(TELEGRAM_API_ID)
        api_hash = str(TELEGRAM_API_HASH)
        
        client = TelegramClient(
            StringSession(),
            api_id,
            api_hash
        )
        
        await client.connect()
        
        result = await client.send_code_request(phone)
        
        # Save the session string and hash, NOT the client object
        context.user_data['session_string'] = client.session.save()
        context.user_data['phone_code_hash'] = result.phone_code_hash
        
        logger.info(f"Code sent successfully for {phone}")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Resend Code", callback_data="resend_code")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sell")]
        ])
        
        await update.message.reply_text(
            f"✅ **Verification Code Sent!**\n\n"
            f"📱 **Important:** Check your Telegram app!\n"
            f"The code should appear in a chat from \"Telegram\" (official)\n\n"
            f"📞 Phone: {phone}\n\n"
            f"📨 Enter the 5-digit code below:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CODE
        
    except FloodWaitError as e:
        await update.message.reply_text(
            f"❌ Too many requests. Please wait {e.seconds} seconds and try again.",
            reply_markup=get_cancel_keyboard()
        )
        return ConversationHandler.END
        
    except PhoneNumberInvalidError:
        await update.message.reply_text(
            "❌ Invalid phone number. Please try again with a valid number.",
            reply_markup=get_cancel_keyboard()
        )
        return PHONE
        
    except Exception as e:
        logger.error(f"Error sending code to {phone}: {e}")
        await update.message.reply_text(
            "❌ An error occurred while sending the verification code.\n"
            "Please try again later or contact support.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        if client and client.is_connected():
            await client.disconnect()

async def resend_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    phone = context.user_data.get('phone')
    
    if not phone:
        await query.edit_message_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    client = None
    try:
        api_id = int(TELEGRAM_API_ID)
        api_hash = str(TELEGRAM_API_HASH)
        
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        
        result = await client.send_code_request(phone)
        
        context.user_data['session_string'] = client.session.save()
        context.user_data['phone_code_hash'] = result.phone_code_hash
        
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
    finally:
        if client and client.is_connected():
            await client.disconnect()

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().replace('-', '').replace(' ', '')
    
    if not code.isdigit():
        await update.message.reply_text(
            "❌ Invalid code format. Please enter only numbers.",
            reply_markup=get_cancel_keyboard()
        )
        return CODE
    
    phone = context.user_data.get('phone')
    phone_code_hash = context.user_data.get('phone_code_hash')
    session_string = context.user_data.get('session_string')
    
    if not phone or not phone_code_hash or not session_string:
        await update.message.reply_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    client = None
    try:
        api_id = int(TELEGRAM_API_ID)
        api_hash = str(TELEGRAM_API_HASH)
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()

        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        
        final_session_string = client.session.save()
        context.user_data['session_string'] = final_session_string
        
        logger.info(f"User signed in successfully with phone {phone}")
        
        await update.message.reply_text(
            "✅ Code verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
        context.user_data['telethon_client'] = client 
        result = await process_account(update, context)
        return result
        
    except SessionPasswordNeededError:
        context.user_data['session_string'] = client.session.save()
        
        await update.message.reply_text(
            "🔐 **2FA Enabled**\n\n"
            "Please send your 2FA password.\n\n"
            "⚠️ **Note:** Your password will be deleted immediately after sending.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return PASSWORD
        
    except PhoneCodeInvalidError:
        await update.message.reply_text(
            "❌ Invalid verification code. Please try again.",
            reply_markup=get_cancel_keyboard()
        )
        return CODE
        
    except Exception as e:
        logger.error(f"Error during sign in: {e}")
        await update.message.reply_text(
            "❌ An error occurred during verification.\n\n"
            f"**Error:** Unable to verify code.\n\n"
            "Please try again or contact support.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        if 'telethon_client' not in context.user_data and client and client.is_connected():
             await client.disconnect()

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    
    await update.message.delete()
    
    session_string = context.user_data.get('session_string')
    if not session_string:
        await update.message.reply_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    client = None
    try:
        api_id = int(TELEGRAM_API_ID)
        api_hash = str(TELEGRAM_API_HASH)
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()

        await client.sign_in(password=password)
        
        session_string = client.session.save()
        context.user_data['session_string'] = session_string
        context.user_data['original_password'] = password
        
        await update.message.reply_text(
            "✅ Password verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
        context.user_data['telethon_client'] = client
        result = await process_account(update, context)
        return result
        
    except PasswordHashInvalidError:
        await update.message.reply_text(
            "❌ Invalid 2FA password. Please try again.",
            reply_markup=get_cancel_keyboard()
        )
        return PASSWORD
        
    except Exception as e:
        logger.error(f"Error with 2FA: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again.",
            reply_markup=get_cancel_keyboard()
        )
        return ConversationHandler.END
    finally:
        if 'telethon_client' not in context.user_data and client and client.is_connected():
             await client.disconnect()

async def process_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('telethon_client')
    phone = context.user_data.get('phone')
    session_string = context.user_data.get('session_string')
    original_password = context.user_data.get('original_password')
    
    if not client:
        await update.message.reply_text("❌ Critical Error: Client session lost. Please start over.")
        return ConversationHandler.END
        
    try:
        await update.message.reply_text("🔄 Step 1/2: Securing 2FA password...")
        await asyncio.sleep(1)
        
        try:
            password_settings = await client(functions.account.GetPasswordRequest())
            
            if password_settings.has_password:
                if original_password:
                    # Change existing password
                    await client.edit_2fa(
                        current_password=original_password,
                        new_password='5000' # You can change this to a secure, random password
                    )
                    await update.message.reply_text("✅ Password reset to default (5000)")
                else:
                    await update.message.reply_text("⚠️ Cannot reset password (no current password provided). Skipping.")
            else:
                # No 2FA, so we can set one.
                await client.edit_2fa(new_password='5000')
                await update.message.reply_text("✅ Default password set (5000)")
                
        except Exception as e:
            logger.warning(f"Password reset warning: {e}")
            await update.message.reply_text(f"⚠️ Password reset skipped: {e}")
        
        await asyncio.sleep(1)
        
        await update.message.reply_text("🔄 Step 2/2: Saving account to database...")
        await asyncio.sleep(1)
        
        # --- NEW: Save with probation period ---
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
        logger.error(f"Error processing account: {e}")
        await update.message.reply_text(
            f"❌ An error occurred during processing.\n\n"
            f"**Error:** {str(e)[:100]}\n\n"
            f"Your account was not sold. Please contact support.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        if 'original_password' in context.user_data:
            del context.user_data['original_password']
        pass

async def confirm_logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Verifying...")
    
    account_id = context.user_data.get('account_id')
    phone = context.user_data.get('phone')
    session_string = context.user_data.get('session_string')
    
    if not account_id or not session_string:
        await query.edit_message_text(
            "❌ Error: Account data missing. Please contact support."
        )
        await cleanup_client(context)
        context.user_data.clear()
        return ConversationHandler.END
    
    client = None
    try:
        api_id = int(TELEGRAM_API_ID)
        api_hash = str(TELEGRAM_API_HASH)
        
        client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash
        )
        await client.connect()
        
        is_authorized = await client.is_user_authorized()
        
        if not is_authorized:
            await query.edit_message_text("❌ Session verification failed. Please try the login process again.")
            await cleanup_client(context)
            context.user_data.clear()
            return ConversationHandler.END
        
        # Mark the account as fully 'active' in the pool
        db.mark_account_active(account_id)
        
        account_price = db.get_account_price()
        db.update_user_balance(update.effective_user.id, account_price, balance_type='seller')
        
        user = db.get_user(update.effective_user.id)
        referred_by = user.get('referred_by')
        
        if referred_by:
            commission_rate = db.get_referral_commission()
            commission = account_price * commission_rate
            db.update_referral_earnings(referred_by, commission)
        
        user_after_payment = db.get_user(update.effective_user.id)
        new_balance = float(user_after_payment['seller_balance'])

        # --- NEW: Added 30-day warning ---
        await query.edit_message_text(
            f"🎉 **Sale Completed Successfully!**\n\n"
            f"💰 **Payment:** ${account_price:.2f} added to your balance\n"
            f"💵 **New Balance:** ${new_balance:.2f}\n"
            f"🆔 **Account ID:** #{account_id}\n\n"
            f"⚠️ **Security Notice:** This payment is conditional. If this account is reclaimed within **30 days**, a **${account_price:.2f} penalty** will be deducted from your balance.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Account sale completed for user {update.effective_user.id}, phone {phone}")
        
    except Exception as e:
        logger.error(f"Error during payment: {e}")
        await query.edit_message_text(
            f"❌ Payment failed. Please contact support with account ID: {account_id}"
        )
    
    finally:
        await cleanup_client(context) # Clean up the client from process_account
        if client and client.is_connected(): # Clean up the verification client
            await client.disconnect()
        context.user_data.clear()
        return ConversationHandler.END

async def cancel_sale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Sale cancelled. Your account was not sold."
    )
    
    await cleanup_client(context)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_client(context)
    context.user_data.clear()
    
    if update.message:
        await update.message.reply_text(
            "❌ Account selling cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "❌ Account selling cancelled."
        )
    
    return ConversationHandler.END

async def cleanup_client(context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('telethon_client')
    if client:
        try:
            if client.is_connected():
                await client.disconnect()
        except:
            pass
        if 'telethon_client' in context.user_data:
            del context.user_data['telethon_client']

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