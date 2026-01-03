import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered, 
    UserDeactivated, 
    SessionRevoked, 
    UserRestricted
)
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, ADMIN_IDS, BUYER_BOT_TOKEN as BOT_TOKEN
from telegram import Bot
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
bot = None

async def get_bot():
    """Initializes and returns the bot instance."""
    global bot
    if bot is None:
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found for checker")
            return None
        bot = Bot(token=BOT_TOKEN)
    return bot

async def handle_banned_account(account, reason):
    """
    Marks an account as banned and applies a penalty if it's within
    the probation period.
    """
    account_id = account['id']
    
    # Update status in DB
    db.update_account_status(account_id, 'banned', is_banned=True)
    db.log_account_usage(account_id, 0, None, 'status_check', False, reason)
    
    # Check if account is still in probation
    probation_ends_at = account.get('probation_ends_at')
    if probation_ends_at and probation_ends_at > datetime.now():
        seller_id = account['seller_user_id']
        penalty = float(account['sold_price'])
        
        if seller_id == 0 or penalty == 0:
            logger.info(f"Account #{account_id} was admin-added. No penalty.")
            return

        logger.warning(f"Account #{account_id} (Seller: {seller_id}) banned within probation. Applying ${penalty} penalty.")
        
        # 1. Deduct from seller's balance
        db.update_user_balance(seller_id, -penalty, balance_type='seller')
        
        # 2. Mark probation as 'completed' to prevent double penalty
        db.connection.cursor().execute(
            "UPDATE sold_accounts SET probation_ends_at = %s WHERE id = %s",
            (datetime.now(), account_id)
        )
        
        # 3. Notify the seller
        try:
            telegram_bot = await get_bot()
            if telegram_bot:
                await telegram_bot.send_message(
                    chat_id=seller_id,
                    text=f"❌ **Account Reclaimed**\n\n"
                         f"The account `{account['phone_number']}` you sold was reclaimed or banned within the 30-day security period.\n\n"
                         f"A penalty of **${penalty:.2f}** has been deducted from your balance.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Failed to send penalty notification to user {seller_id}: {e}")

async def check_single_account(account):
    account_id = account['id']
    session_string = account['session_string']
    
    client = Client(
        name=f"chk_{account_id}",
        api_id=int(TELEGRAM_API_ID),
        api_hash=TELEGRAM_API_HASH,
        session_string=session_string,
        in_memory=True,
        no_updates=True
    )
    
    try:
        await client.connect()
        me = await client.get_me()
        
        if me.is_restricted:
            logger.warning(f"Account #{account_id} is restricted")
            await handle_banned_account(account, 'Account restricted')
            return {'status': 'banned', 'reason': 'Restricted'}
            
        # If it was banned but now works, unban it
        if account['is_banned']:
            logger.info(f"Account #{account_id} recovered. Unbanning.")
            db.update_account_status(account_id, 'active', is_banned=False)
            
        db.log_account_usage(account_id, 0, None, 'status_check', True, None)
        return {'status': 'active', 'reason': 'OK'}
        
    except (AuthKeyUnregistered, UserDeactivated, SessionRevoked) as e:
        logger.error(f"Account #{account_id} banned: {type(e).__name__}")
        await handle_banned_account(account, type(e).__name__)
        return {'status': 'banned', 'reason': 'Session Invalid'}
    except Exception as e:
        logger.error(f"Error checking {account_id}: {e}")
        db.log_account_usage(account_id, 0, None, 'status_check', False, str(e))
        return {'status': 'error', 'reason': str(e)}
    finally:
        try:
            await client.disconnect()
        except: pass

async def check_all_accounts():
    accounts = db.get_all_accounts(limit=1000)
    logger.info(f"Checking {len(accounts)} accounts...")
    
    results = []
    for acc in accounts:
        res = await check_single_account(acc)
        results.append(res)
        await asyncio.sleep(1) # Rate limit
    
    return results

async def check_pool_and_alert():
    logger.info("Checking account pool status...")
    stats = db.get_account_pool_stats()
    
    if stats['active_accounts'] < 100:
        await send_low_pool_alert(stats['active_accounts'], stats['total_accounts'])

async def send_low_pool_alert(active, total):
    bot = await get_bot()
    if not bot or not ADMIN_IDS: return
    
    msg = f"🚨 **LOW POOL ALERT**\n\nActive: {active}\nTotal: {total}\nThreshold: 100"
    for admin in ADMIN_IDS:
        try:
            await bot.send_message(admin, msg, parse_mode='Markdown')
        except: pass

async def main():
    await check_all_accounts()
    await check_pool_and_alert()

if __name__ == "__main__":
    asyncio.run(main())