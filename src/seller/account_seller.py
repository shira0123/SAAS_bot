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
        
        session_string = client.session.save()
        context.user_data['session_string'] = session_string
        context.user_data['phone_code_hash'] = result.phone_code_hash
        context.user_data['telethon_client'] = client
        
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
            f"⏰ If you don't see it within 2 minutes:\n"
            f"   • Check the \"Telegram\" chat in your app\n"
            f"   • Check your SMS messages\n"
            f"   • Use the Resend button below\n\n"
            f"📨 Enter the 5-digit code below:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return CODE
        
    except FloodWaitError as e:
        await cleanup_client(context)
        await update.message.reply_text(
            f"❌ Too many requests. Please wait {e.seconds} seconds and try again.",
            reply_markup=get_cancel_keyboard()
        )
        return ConversationHandler.END
        
    except PhoneNumberInvalidError:
        await cleanup_client(context)
        await update.message.reply_text(
            "❌ Invalid phone number. Please try again with a valid number.",
            reply_markup=get_cancel_keyboard()
        )
        return PHONE
        
    except Exception as e:
        await cleanup_client(context)
        logger.error(f"Error sending code to {phone}: {e}")
        await update.message.reply_text(
            "❌ An error occurred while sending the verification code.\n\n"
            "**Error details:** Unable to connect to Telegram servers\n\n"
            "Please try again later or contact support.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def resend_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    phone = context.user_data.get('phone')
    client = context.user_data.get('telethon_client')
    
    if not phone:
        await query.edit_message_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    try:
        if not client or not client.is_connected():
            api_id = int(TELEGRAM_API_ID)
            api_hash = str(TELEGRAM_API_HASH)
            
            if client:
                await cleanup_client(context)
            
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            context.user_data['telethon_client'] = client
        
        result = await client.send_code_request(phone)
        
        session_string = client.session.save()
        context.user_data['session_string'] = session_string
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
    client = context.user_data.get('telethon_client')
    
    if not client or not phone or not phone_code_hash:
        await update.message.reply_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        
        final_session_string = client.session.save()
        context.user_data['session_string'] = final_session_string
        
        logger.info(f"User signed in successfully with phone {phone}")
        
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
            "⚠️ **Note:** Your password will be deleted immediately after sending for security.",
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
            "**Error:** Unable to verify code\n\n"
            "Please try again or contact support.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    
    await update.message.delete()
    
    client = context.user_data.get('telethon_client')
    
    if not client:
        await update.message.reply_text("❌ Session expired. Please start over.")
        return ConversationHandler.END
    
    try:
        await client.sign_in(password=password)
        
        session_string = client.session.save()
        context.user_data['session_string'] = session_string
        context.user_data['original_password'] = password
        
        await update.message.reply_text(
            "✅ Password verified successfully!\n\n"
            "⏳ Processing your account..."
        )
        
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

async def process_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = context.user_data.get('telethon_client')
    phone = context.user_data.get('phone')
    session_string = context.user_data.get('session_string')
    original_password = context.user_data.get('original_password')
    
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
        
        await update.message.reply_text("🔄 Step 2/3: Resetting 2FA password...")
        await asyncio.sleep(1)
        
        try:
            password_settings = await client(functions.account.GetPasswordRequest())
            
            if password_settings.has_password:
                if original_password:
                    await client.edit_2fa(
                        current_password=original_password,
                        new_password='5000'
                    )
                    await update.message.reply_text("✅ Password reset to default (5000)")
                else:
                    await update.message.reply_text("⚠️ Cannot reset password (no current password)")
            else:
                await client.edit_2fa(new_password='5000')
                await update.message.reply_text("✅ Default password set (5000)")
                
        except Exception as e:
            logger.warning(f"Password reset warning: {e}")
            await update.message.reply_text("⚠️ Password reset skipped")
        
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
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm & Complete Sale", callback_data="confirm_logout")],
            [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
        ])
        
        await update.message.reply_text(
            "📱 **Final Step - Confirmation**\n\n"
            "✅ Other sessions terminated\n"
            "✅ Password reset complete\n"
            "✅ Session saved to our system\n"
            "✅ Ready for payment\n\n"
            "⚠️ **IMPORTANT:** You should now manually log out from your Telegram app on all devices before confirming.\n\n"
            "Once you've logged out and are ready, click Confirm to complete the sale and receive payment.\n\n"
            "**Note:** By confirming, you agree that we now have full control of this account.",
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

async def confirm_logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
    
    try:
        api_id = int(TELEGRAM_API_ID)
        api_hash = str(TELEGRAM_API_HASH)
        
        verification_client = TelegramClient(
            StringSession(session_string),
            api_id,
            api_hash
        )
        await verification_client.connect()
        
        is_authorized = await verification_client.is_user_authorized()
        await verification_client.disconnect()
        
        if not is_authorized:
            await query.edit_message_text("❌ Session verification failed. Account may not be properly logged out.")
            await cleanup_client(context)
            context.user_data.clear()
            return ConversationHandler.END
        
        account_price = db.get_account_price()
        db.add_balance(update.effective_user.id, account_price, balance_type='seller')
        
        referred_by = db.get_user(update.effective_user.id).get('referred_by')
        if referred_by:
            from src.database.config import REFERRAL_COMMISSION
            commission = account_price * REFERRAL_COMMISSION
            db.add_balance(referred_by, commission, balance_type='referral')
            db.log_referral_earning(referred_by, update.effective_user.id, commission)
        
        await query.edit_message_text(
            f"🎉 **Sale Completed Successfully!**\n\n"
            f"💰 **Payment:** ${account_price:.2f} added to your balance\n"
            f"📱 **Phone:** {phone}\n\n"
            f"Thank you for selling your account!\n"
            f"You can withdraw your earnings anytime.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Account sale completed for user {update.effective_user.id}, phone {phone}")
        
    except Exception as e:
        logger.error(f"Error during payment: {e}")
        await query.edit_message_text(
            f"❌ Payment failed. Please contact support with account ID: {account_id}"
        )
    
    finally:
        await cleanup_client(context)
        context.user_data.clear()
        return ConversationHandler.END

async def cancel_sale_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Sale cancelled. Your account was not sold.\n\n"
        "No changes have been made to your account."
    )
    
    await cleanup_client(context)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_client(context)
    context.user_data.clear()
    
    if update.message:
        await update.message.reply_text(
            "❌ Account selling cancelled.\n\n"
            "You can start again anytime using the menu.",
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
