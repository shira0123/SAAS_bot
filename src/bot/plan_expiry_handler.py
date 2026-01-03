import sys
import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import asyncio
import logging
from pyrogram import Client
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, BUYER_BOT_TOKEN
from telegram import Bot
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlanExpiryHandler:
    def __init__(self):
        self.db = Database()
        self.bot = None

    async def initialize_bot(self):
        if not self.bot:
            self.bot = Bot(token=BUYER_BOT_TOKEN)

    async def send_expiry_reminder(self, user_id, order, days_left):
        """Send warning notification"""
        await self.initialize_bot()
        try:
            msg = (
                f"⏰ **Plan Expiry Reminder**\n\n"
                f"Plan #{order['id']} ({order['plan_type']})\n"
                f"Channel: @{order['channel_username']}\n"
                f"Expires in: **{days_left} day(s)**\n\n"
                f"Please renew via 'My Plans' to avoid service interruption."
            )
            await self.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")

    async def send_final_expiry_notification(self, user_id, order, leave_count):
        """Send final notification after accounts leave"""
        await self.initialize_bot()
        try:
            msg = (
                f"❌ **Plan Expired**\n\n"
                f"Plan #{order['id']} for @{order['channel_username']} has ended.\n"
                f"📉 {leave_count} accounts have left the channel.\n\n"
                f"To continue, please buy a new plan."
            )
            await self.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send final note: {e}")

    async def handle_expired_order_auto_leave(self, order):
        order_id = order['id']
        channel = order['channel_username']
        
        # Get accounts that worked on this order
        usage_logs = self.db.connection.cursor()
        usage_logs.execute("""
            SELECT DISTINCT account_id FROM account_usage_logs 
            WHERE order_id = %s AND action_type IN ('channel_join', 'join')
        """, (order_id,))
        rows = usage_logs.fetchall()
        ids = [row['account_id'] for row in rows]
        usage_logs.close()
        
        left_count = 0
        for acc_id in ids:
            account = self.db.get_account_by_id(acc_id)
            if not account: continue
            
            # Using Pyrogram to leave
            try:
                client = Client(
                    name=f"lv_{acc_id}",
                    api_id=int(TELEGRAM_API_ID),
                    api_hash=TELEGRAM_API_HASH,
                    session_string=account['session_string'],
                    in_memory=True,
                    no_updates=True
                )
                await client.connect()
                await client.leave_chat(channel)
                left_count += 1
                self.db.decrement_account_join_count(acc_id)
                self.db.log_account_usage(acc_id, order_id, channel, 'leave', True)
                await client.disconnect()
            except Exception as e:
                logger.error(f"Leave failed {acc_id}: {e}")
        
        self.db.update_order_status(order_id, 'expired')
        await self.send_final_expiry_notification(order['user_id'], order, left_count)

    async def run(self):
        logger.info("Plan Expiry Handler (Pyrogram) Started")
        while True:
            try:
                active_orders = self.db.get_active_orders()
                now = datetime.now()
                
                for order in active_orders:
                    if not order.get('expires_at'): continue
                    
                    days_until_expiry = (order['expires_at'] - now).days
                    
                    # 1. Send Reminders (3 days or 1 day left)
                    if days_until_expiry in [3, 1]:
                        await self.send_expiry_reminder(order['user_id'], order, days_until_expiry)

                    # 2. Handle Expiry (Grace period check)
                    if days_until_expiry < -3:
                        await self.handle_expired_order_auto_leave(order)
                
                await asyncio.sleep(3600 * 4) # Run every 4 hours to be safe
            except Exception as e:
                logger.error(f"Expiry Loop Error: {e}")
                await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(PlanExpiryHandler().run())