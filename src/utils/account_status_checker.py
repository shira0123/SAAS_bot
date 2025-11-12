import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyUnregisteredError, UserDeactivatedError, SessionRevokedError
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, ADMIN_IDS, BUYER_BOT_TOKEN as BOT_TOKEN
from telegram import Bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

async def check_single_account(account):
    account_id = account['id']
    phone = account['phone_number']
    session_string = account['session_string']
    
    logger.info(f"Checking account #{account_id} ({phone})")
    
    client = None
    try:
        client = TelegramClient(
            StringSession(session_string),
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.warning(f"Account #{account_id} is not authorized")
            db.update_account_status(account_id, 'banned', is_banned=True)
            db.log_account_usage(account_id, 0, None, 'status_check', False, 'Not authorized')
            return {
                'account_id': account_id,
                'phone': phone,
                'status': 'banned',
                'reason': 'Not authorized'
            }
        
        me = await client.get_me()
        
        if me.restricted:
            logger.warning(f"Account #{account_id} is restricted")
            db.update_account_status(account_id, 'banned', is_banned=True)
            db.log_account_usage(account_id, 0, None, 'status_check', False, 'Account restricted')
            return {
                'account_id': account_id,
                'phone': phone,
                'status': 'banned',
                'reason': 'Account restricted'
            }
        
        dialogs = await client.get_dialogs(limit=1)
        
        if account['is_banned']:
            logger.info(f"Account #{account_id} is now active again")
            db.update_account_status(account_id, 'active', is_banned=False)
        
        db.log_account_usage(account_id, 0, None, 'status_check', True, None)
        
        logger.info(f"Account #{account_id} is active and working")
        return {
            'account_id': account_id,
            'phone': phone,
            'status': 'active',
            'reason': 'Working normally'
        }
        
    except (AuthKeyUnregisteredError, UserDeactivatedError, SessionRevokedError) as e:
        logger.error(f"Account #{account_id} is banned: {type(e).__name__}")
        db.update_account_status(account_id, 'banned', is_banned=True)
        db.log_account_usage(account_id, 0, None, 'status_check', False, type(e).__name__)
        return {
            'account_id': account_id,
            'phone': phone,
            'status': 'banned',
            'reason': type(e).__name__
        }
    except Exception as e:
        logger.error(f"Error checking account #{account_id}: {e}")
        db.log_account_usage(account_id, 0, None, 'status_check', False, str(e))
        return {
            'account_id': account_id,
            'phone': phone,
            'status': 'error',
            'reason': str(e)
        }
    finally:
        if client and client.is_connected():
            await client.disconnect()
            logger.debug(f"Disconnected client for account #{account_id}")

async def check_all_accounts():
    logger.info("Starting account status check...")
    
    accounts = db.get_all_accounts(limit=1000, offset=0)
    
    if not accounts:
        logger.info("No accounts to check")
        return []
    
    logger.info(f"Found {len(accounts)} accounts to check")
    
    results = []
    
    for account in accounts:
        result = await check_single_account(account)
        results.append(result)
        await asyncio.sleep(2)
    
    logger.info(f"Account check complete. Checked {len(results)} accounts")
    
    active_count = sum(1 for r in results if r['status'] == 'active')
    banned_count = sum(1 for r in results if r['status'] == 'banned')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    logger.info(f"Results: {active_count} active, {banned_count} banned, {error_count} errors")
    
    return results

async def check_pool_and_alert():
    logger.info("Checking account pool status...")
    
    stats = db.get_account_pool_stats()
    
    active_accounts = stats['active_accounts']
    total_accounts = stats['total_accounts']
    
    logger.info(f"Pool status: {active_accounts} active out of {total_accounts} total")
    
    if active_accounts < 100:
        logger.warning(f"LOW POOL ALERT: Only {active_accounts} active accounts remaining!")
        await send_low_pool_alert(active_accounts, total_accounts)
    
    return stats

async def send_low_pool_alert(active_accounts, total_accounts):
    if not BOT_TOKEN or not ADMIN_IDS:
        logger.error("Cannot send alert: BOT_TOKEN or ADMIN_IDS not configured")
        return
    
    try:
        bot = Bot(token=BOT_TOKEN)
        
        alert_message = f"""
🚨 **LOW ACCOUNT POOL ALERT** 🚨

⚠️ **Warning:** Active account pool is critically low!

📊 **Current Status:**
• Active Accounts: {active_accounts}
• Total Accounts: {total_accounts}
• Threshold: 100 accounts

**Action Required:**
1. Review banned accounts and try to recover
2. Purchase more accounts from sellers
3. Add accounts manually if needed

Use /accounts to manage the pool.
"""
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=alert_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Low pool alert sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send alert to admin {admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error sending low pool alert: {e}")

async def main():
    results = await check_all_accounts()
    
    print("\n" + "="*50)
    print("ACCOUNT STATUS CHECK COMPLETE")
    print("="*50)
    
    for result in results:
        status_emoji = "✅" if result['status'] == 'active' else "🚫" if result['status'] == 'banned' else "❌"
        print(f"{status_emoji} #{result['account_id']} {result['phone']}: {result['status']} - {result['reason']}")
    
    print("="*50 + "\n")
    
    await check_pool_and_alert()

if __name__ == "__main__":
    asyncio.run(main())
