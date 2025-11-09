import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import LeaveChannelRequest
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, ADMIN_IDS
from datetime import datetime, timedelta
from telegram import Bot
from src.database.config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PlanExpiryHandler:
    def __init__(self):
        self.db = Database()
        self.bot = None
        
    async def initialize_bot(self):
        """Initialize Telegram bot for notifications"""
        if not self.bot:
            self.bot = Bot(token=BOT_TOKEN)
    
    async def send_expiry_reminder(self, user_id, order, days_until_expiry):
        """Send expiry reminder notification to user"""
        await self.initialize_bot()
        
        try:
            plan_type_display = {
                'unlimited_views': '💎 Unlimited Views',
                'limited_views': '🎯 Limited Views',
                'unlimited_reactions': '❤️ Unlimited Reactions',
                'limited_reactions': '🎪 Limited Reactions'
            }.get(order['plan_type'], order['plan_type'])
            
            if days_until_expiry > 0:
                message = f"""
⏰ **Plan Expiry Reminder**

Your plan is expiring soon!

📊 Plan #{order['id']} - {plan_type_display}
📺 Channel: @{order['channel_username']}
⏳ Expires in: **{days_until_expiry} day(s)**

💡 **What happens next:**
• Your plan will expire on {order['expires_at'].strftime('%Y-%m-%d %H:%M')}
• You have a 3-day grace period to renew
• After the grace period, accounts will leave the channel

🔄 **To renew your plan:**
Use the "My Plans" button to renew before it expires!
"""
            else:
                message = f"""
⚠️ **Plan Expired**

Your plan has expired today!

📊 Plan #{order['id']} - {plan_type_display}
📺 Channel: @{order['channel_username']}

💡 **Grace Period:**
• You have 3 days to renew this plan
• If not renewed, accounts will leave the channel
• Use "My Plans" to renew now!
"""
            
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"Sent expiry reminder to user {user_id} for order {order['id']}")
            
        except Exception as e:
            logger.error(f"Error sending expiry reminder to user {user_id}: {e}")
    
    async def check_and_send_reminders(self):
        """Check for orders that need expiry reminders and send notifications"""
        logger.info("Checking for orders needing expiry reminders...")
        
        active_orders = self.db.get_active_orders()
        
        for order in active_orders:
            if not order.get('expires_at'):
                continue
            
            expires_at = order['expires_at']
            now = datetime.now()
            days_until_expiry = (expires_at - now).days
            
            if days_until_expiry in [3, 1]:
                await self.send_expiry_reminder(order['user_id'], order, days_until_expiry)
            
            elif days_until_expiry <= 0 and days_until_expiry >= -3:
                if days_until_expiry == 0:
                    await self.send_expiry_reminder(order['user_id'], order, 0)
                
                continue
            
            elif days_until_expiry < -3:
                logger.info(f"Order {order['id']} is past grace period, triggering auto-leave")
                await self.handle_expired_order_auto_leave(order)
    
    async def handle_expired_order_auto_leave(self, order):
        """Handle expired order by making accounts leave the channel"""
        order_id = order['id']
        channel_username = order['channel_username']
        
        logger.info(f"Processing auto-leave for expired order {order_id}")
        
        usage_logs = self.db.connection.cursor()
        usage_logs.execute("""
            SELECT DISTINCT account_id 
            FROM account_usage_logs
            WHERE order_id = %s AND action_type IN ('channel_join', 'view_delivery', 'reaction_delivery')
        """, (order_id,))
        account_ids = [row['account_id'] for row in usage_logs.fetchall()]
        usage_logs.close()
        
        logger.info(f"Found {len(account_ids)} accounts to remove from channel {channel_username}")
        
        leave_count = 0
        for account_id in account_ids:
            try:
                account = self.db.get_account_by_id(account_id)
                if not account:
                    continue
                
                session_string = account['session_string']
                
                client = TelegramClient(
                    StringSession(session_string),
                    TELEGRAM_API_ID,
                    TELEGRAM_API_HASH
                )
                await client.connect()
                
                if await client.is_user_authorized():
                    try:
                        entity = await client.get_entity(channel_username)
                        await client(LeaveChannelRequest(entity))
                        
                        self.db.log_account_usage(
                            account_id, order_id, channel_username,
                            'channel_leave', success=True
                        )
                        
                        cursor = self.db.connection.cursor()
                        cursor.execute("""
                            UPDATE sold_accounts
                            SET join_count = GREATEST(0, join_count - 1)
                            WHERE id = %s
                        """, (account_id,))
                        cursor.close()
                        
                        leave_count += 1
                        logger.info(f"Account {account_id} left channel {channel_username}")
                        
                    except Exception as e:
                        logger.error(f"Error leaving channel with account {account_id}: {e}")
                        self.db.log_account_usage(
                            account_id, order_id, channel_username,
                            'channel_leave', success=False, error_message=str(e)
                        )
                
                await client.disconnect()
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing account {account_id} for auto-leave: {e}")
                continue
        
        logger.info(f"Auto-leave complete for order {order_id}: {leave_count} accounts left the channel")
        
        self.db.update_order_status(order_id, 'expired')
        
        await self.send_final_expiry_notification(order['user_id'], order, leave_count)
    
    async def send_final_expiry_notification(self, user_id, order, leave_count):
        """Send final notification after auto-leave"""
        await self.initialize_bot()
        
        try:
            message = f"""
❌ **Plan Expired**

Your plan has been terminated after the grace period.

📊 Plan #{order['id']}
📺 Channel: @{order['channel_username']}
👥 {leave_count} accounts have left the channel

💡 To continue service, please purchase a new plan using the 💎 Buy Plan button.
"""
            
            await self.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            logger.info(f"Sent final expiry notification to user {user_id} for order {order['id']}")
            
        except Exception as e:
            logger.error(f"Error sending final expiry notification to user {user_id}: {e}")
    
    async def run(self):
        """Main scheduler loop - runs every hour"""
        logger.info("Plan Expiry Handler started")
        
        while True:
            try:
                await self.check_and_send_reminders()
                
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in expiry handler loop: {e}")
                await asyncio.sleep(600)

async def main():
    handler = PlanExpiryHandler()
    try:
        await handler.run()
    except KeyboardInterrupt:
        logger.info("Expiry handler interrupted by user")

if __name__ == '__main__':
    asyncio.run(main())
