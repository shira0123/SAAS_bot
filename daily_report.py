import asyncio
import logging
from telegram import Bot
from database import Database
from config import BOT_TOKEN, ADMIN_IDS
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

async def send_daily_report():
    if not BOT_TOKEN or not ADMIN_IDS:
        logger.error("BOT_TOKEN or ADMIN_IDS not configured")
        return
    
    try:
        bot = Bot(token=BOT_TOKEN)
        
        daily_stats = db.get_daily_stats()
        system_stats = db.get_system_stats()
        saas_stats = db.get_saas_daily_stats()
        pool_stats = db.get_account_pool_stats()
        
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        report_message = f"""
📊 **Comprehensive Daily Report - {report_date}**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**💎 SaaS Sales & Deposits (Today)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Revenue Today: ${saas_stats.get('revenue_today', 0):.2f}
📦 New Orders: {saas_stats.get('new_orders_today', 0)}
✅ Active Plans: {saas_stats.get('active_plans', 0)}
📈 Orders This Week: {saas_stats.get('orders_this_week', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**📈 Seller Accounts (Today)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 New Accounts Sold: {daily_stats['new_accounts_24h']}
🚫 New Banned Accounts: {daily_stats['new_bans_24h']}
👥 New Users Registered: {daily_stats['new_users_24h']}
💸 Seller Withdrawals: ${daily_stats['withdrawn_24h']:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**📱 TG Account Pool Status**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Total Accounts: {pool_stats['total_accounts']}
✅ Active & Ready: {pool_stats['active_accounts']}
🚫 Banned: {pool_stats['banned_accounts']}
📦 Full: {pool_stats['full_accounts']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**👥 Overall System Stats**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Total Users: {system_stats['total_users']}
• Banned Users: {system_stats['banned_users']}
• Total Accounts Ever: {system_stats['total_accounts_sold']}

💰 **Financial Summary:**
• Seller Balances: ${system_stats['total_seller_balance']:.2f}
• Total Withdrawn: ${system_stats['total_withdrawn']:.2f}
• Referral Earnings: ${system_stats['total_referral_earnings']:.2f}

💸 **Pending Actions:**
• Withdrawal Requests: {system_stats['pending_withdrawals']}
• New Requests (24h): {daily_stats['new_withdrawals_24h']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=report_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Daily report sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send report to admin {admin_id}: {e}")
        
        logger.info("Daily report process completed")
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")

if __name__ == "__main__":
    asyncio.run(send_daily_report())
