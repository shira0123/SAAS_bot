import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    ChannelPrivateError,
    UserBannedInChannelError,
    FloodWaitError,
    InviteHashExpiredError,
)
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetMessagesViewsRequest
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ServiceDeliveryWorker:
    def __init__(self):
        self.db = Database()
        self.active_channels = {} 
        self.active_clients = {}
        self.monitored_orders = set()

    async def create_client_from_session(self, account_id, session_string):
        """Create a Telethon client with strict timeout"""
        try:
            client = TelegramClient(
                StringSession(session_string),
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH,
                connection_retries=1,
                timeout=15,
                auto_reconnect=False
            )
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error(f"❌ Account {account_id}: Session invalid/unauthorized")
                self.db.update_account_status(account_id, 'banned', is_banned=True)
                await client.disconnect()
                return None
            
            return client
        except Exception as e:
            logger.error(f"❌ Account {account_id}: Connection failed: {e}")
            return None

    async def get_client_for_account(self, account):
        account_id = account['id']
        if account_id in self.active_clients:
            client = self.active_clients[account_id]
            if client.is_connected():
                return client
        
        client = await self.create_client_from_session(account_id, account['session_string'])
        if client:
            self.active_clients[account_id] = client
        return client

    async def join_channel(self, client, account_id, channel_username, order_id):
        try:
            entity = None
            if 'joinchat' in channel_username or 't.me/+' in channel_username:
                hash_code = channel_username.split('/')[-1].replace('+', '')
                updates = await client(ImportChatInviteRequest(hash_code))
                entity = updates.chats[0]
            else:
                clean_username = channel_username.replace('@', '').replace('https://t.me/', '')
                entity = await client.get_entity(clean_username)
                await client(JoinChannelRequest(entity))
            
            self.db.increment_account_join_count(account_id)
            self.db.log_account_usage(account_id, order_id, channel_username, 'channel_join', True)
            logger.info(f"✅ Account {account_id} joined {channel_username}")
            return entity
        except Exception as e:
            logger.warning(f"⚠️ Account {account_id} failed to join: {e}")
            return None

    async def execute_join_and_leave_order(self, order):
        order_id = order['id']
        channel = order['channel_username']
        target = order['views_per_post']
        posts = order['total_posts']
        
        # Use the plan's delay, but enforce a 2s minimum for "Instant" to allow 'settling'
        plan_delay = order.get('delay_seconds', 0)
        actual_delay = max(2, plan_delay)
        
        logger.info(f"🚀 Order #{order_id}: Starting {order['plan_type']} (Target: {target}, Delay: {actual_delay}s)")
        
        clients_in_job = {} # {account_id: client}
        failed_ids = []
        channel_entity = None
        
        # --- PHASE 1: JOINING ---
        for attempt in range(3):
            needed = target - len(clients_in_job)
            if needed <= 0: break
            
            logger.info(f"Order #{order_id}: Fetching {needed} accounts (Attempt {attempt+1}/3)")
            
            batch = self.db.get_available_accounts(limit=needed + 2, exclude_ids=failed_ids)
            
            if not batch:
                logger.info(f"Order #{order_id}: No more accounts in pool.")
                break
                
            for account in batch:
                if len(clients_in_job) >= target: break
                
                try:
                    async with asyncio.timeout(20): 
                        client = await self.get_client_for_account(account)
                        if not client:
                            failed_ids.append(account['id'])
                            continue
                        
                        entity = await self.join_channel(client, account['id'], channel, order_id)
                        if entity:
                            clients_in_job[account['id']] = client
                            if not channel_entity and hasattr(entity, 'id'):
                                channel_entity = entity
                        else:
                            failed_ids.append(account['id'])
                except Exception as e:
                    logger.error(f"Join error acc {account['id']}: {e}")
                    failed_ids.append(account['id'])
            
            if len(clients_in_job) < target:
                await asyncio.sleep(2)

        joined_count = len(clients_in_job)
        logger.info(f"✅ Order #{order_id}: Joining Phase Done. {joined_count}/{target} accounts ready.")

        if joined_count == 0:
            logger.error(f"❌ Order #{order_id} FAILED: 0 accounts joined.")
            self.db.update_order_status(order_id, 'failed')
            return

        # --- PHASE 2: DELIVERY ---
        try:
            monitor = next(iter(clients_in_job.values()))
            
            if not channel_entity or channel_entity is True:
                if 'joinchat' in channel or 't.me/+' in channel:
                    dialogs = await monitor.get_dialogs(limit=1)
                    channel_entity = dialogs[0].entity
                else:
                    channel_entity = await monitor.get_entity(channel.replace('@', ''))

            msgs = await monitor.get_messages(channel_entity, limit=posts)
            
            if not msgs:
                logger.warning(f"Order #{order_id}: Channel is empty.")
            else:
                logger.info(f"Order #{order_id}: Delivering to {len(msgs)} posts...")
                
                for msg in msgs:
                    views_delivered = 0
                    for acc_id, client in clients_in_job.items():
                        try:
                            if 'react' in order['plan_type']:
                                await client.send_reaction(msg.chat_id, msg.id, random.choice(['👍','❤️','🔥','👏']))
                            else:
                                # THE CRITICAL FIX: GetMessagesViewsRequest with increment=True
                                await client(GetMessagesViewsRequest(
                                    peer=channel_entity,
                                    id=[msg.id],
                                    increment=True
                                ))
                            
                            views_delivered += 1
                            
                            # "Settle Time" - Sleep between views to mimic human reading speed
                            await asyncio.sleep(actual_delay)
                            
                        except Exception as e:
                            logger.debug(f"Delivery failed for acc {acc_id}: {e}")
                    
                    self.db.increment_delivered_posts(order_id)
                    logger.info(f"Order #{order_id}: Post {msg.id} serviced by {views_delivered} accounts.")

        except Exception as e:
            logger.error(f"⚠️ Order #{order_id} Delivery Error: {e}")

        # --- PHASE 3: LEAVING (Guaranteed) ---
        logger.info(f"Order #{order_id}: Leaving channel...")
        
        for acc_id, client in clients_in_job.items():
            try:
                if channel_entity and hasattr(channel_entity, 'id'):
                    await client(LeaveChannelRequest(channel_entity))
                    self.db.decrement_account_join_count(acc_id)
            except Exception:
                pass
            finally:
                if client.is_connected():
                    await client.disconnect()
                if acc_id in self.active_clients:
                    del self.active_clients[acc_id]

        self.db.update_order_status(order_id, 'completed')
        logger.info(f"🏁 Order #{order_id} COMPLETED.")

    async def run(self):
        logger.info("Service Delivery Worker started")
        while True:
            try:
                await self.process_new_orders()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(10)

    async def process_new_orders(self):
        orders = self.db.get_active_orders()
        for order in orders:
            if order['id'] in self.monitored_orders: continue
            
            if 'join' in order['plan_type'] or order['duration'] == 0:
                self.monitored_orders.add(order['id'])
                asyncio.create_task(self.execute_join_and_leave_order(order))

async def main():
    if not os.path.exists('sessions'): os.makedirs('sessions')
    worker = ServiceDeliveryWorker()
    await worker.run()

if __name__ == '__main__':
    asyncio.run(main())