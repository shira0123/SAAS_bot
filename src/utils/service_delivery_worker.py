import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import asyncio
import logging
from telethon import TelegramClient, events
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
from datetime import datetime, timedelta, date
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
        """Make an account join a channel (public or private)"""
        try:
            entity = None
            log_action = 'channel_join'
            
            if 'joinchat/' in channel_username or 't.me/+' in channel_username:
                hash_code = channel_username.split('/')[-1].replace('+', '')
                updates = await client(ImportChatInviteRequest(hash_code))
                entity = updates.chats[0]
                log_action = 'private_channel_join'
            else:
                channel_username_clean = channel_username.replace('@', '')
                entity = await client.get_entity(channel_username_clean)
                await client(JoinChannelRequest(entity))
            
            self.db.increment_account_join_count(account_id)
            self.db.log_account_usage(
                account_id, order_id, channel_username, 
                log_action, success=True
            )
            logger.info(f"Account {account_id} successfully joined channel {channel_username}")
            return entity
                    
        except UserBannedInChannelError:
            logger.error(f"Account {account_id} is banned in channel {channel_username}")
            self.db.update_account_status(account_id, 'banned', is_banned=True)
            return None
        except (ValueError, InviteHashExpiredError):
             logger.error(f"Order #{order_id}: Invalid or expired invite link {channel_username}")
             return None
        except FloodWaitError as e:
            # --- FIX: Skip account if wait is too long (>45s) ---
            if e.seconds > 45:
                logger.warning(f"FloodWait of {e.seconds}s for Account {account_id}. SKIPPING to avoid blocking worker.")
                return None
            
            logger.warning(f"Flood wait error for account {account_id}: waiting {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return None
        except Exception as e:
            if "already a participant" in str(e).lower():
                logger.warning(f"Account {account_id} already in channel {channel_username}")
                try:
                    # Return entity if already joined so we can still use it for views
                    if 'joinchat/' in channel_username or 't.me/+' in channel_username:
                        # For private chats, we might need to fetch dialogs to get entity, 
                        # but returning True allows the loop to continue
                        return True 
                    return await client.get_entity(channel_username.replace('@',''))
                except Exception:
                    return True 
            logger.error(f"Error joining channel {channel_username} with account {account_id}: {e}")
            return None

    # ---------------------------------------------------------
    # PART 1: JOIN & LEAVE PLANS (View/React N Posts)
    # ---------------------------------------------------------
    async def execute_join_and_leave_order(self, order):
        order_id = order['id']
        channel = order['channel_username']
        target = order['views_per_post']
        posts = order['total_posts']
        
        plan_delay = order.get('delay_seconds', 0)
        actual_delay = max(2, plan_delay)
        
        logger.info(f"🚀 Order #{order_id}: Starting {order['plan_type']} (Target: {target}, Delay: {actual_delay}s)")
        
        clients_in_job = {}
        failed_ids = []
        channel_entity = None
        
        # --- PHASE 1: JOINING (With Retry Loop) ---
        for attempt in range(3):
            needed = target - len(clients_in_job)
            if needed <= 0: break
            
            logger.info(f"Order #{order_id}: Fetching {needed} accounts (Attempt {attempt+1}/3)")
            
            # Use exclude_ids to get fresh accounts
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
            
            # Ensure we have the entity
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
                reactions_list = ['👍', '❤️', '🔥', '👏', '😍', '🎉', '🤩']
                
                for msg in msgs:
                    views_delivered = 0
                    for acc_id, client in clients_in_job.items():
                        try:
                            if 'react' in order['plan_type']:
                                # Use channel_entity as peer, safer than chat_id
                                reaction = random.choice(reactions_list)
                                await client.send_reaction(channel_entity, msg.id, reaction)
                            else:
                                # The increment=True is critical for view counts
                                await client(GetMessagesViewsRequest(
                                    peer=channel_entity,
                                    id=[msg.id],
                                    increment=True
                                ))
                            
                            views_delivered += 1
                            await asyncio.sleep(actual_delay)
                            
                        except Exception as e:
                            logger.debug(f"Delivery failed for acc {acc_id}: {e}")
                    
                    self.db.increment_delivered_posts(order_id)
                    logger.info(f"Order #{order_id}: Post {msg.id} serviced by {views_delivered} accounts.")

        except Exception as e:
            logger.error(f"⚠️ Order #{order_id} Delivery Error: {e}")

        # --- PHASE 3: LEAVING ---
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

    # ---------------------------------------------------------
    # PART 2: STANDARD PLANS (Unlimited/Limited)
    # ---------------------------------------------------------
    
    async def deliver_views_or_reactions(self, message, order):
        """Delivers views or reactions for standard plans"""
        account_count = order['views_per_post']
        delay_seconds = order.get('delay_seconds', 10) 
        
        # We don't exclude IDs here yet, but we could improve this later
        available_accounts = self.db.get_available_accounts(limit=account_count)
        
        logger.info(f"Order #{order['id']}: Delivering {len(available_accounts)} actions to post {message.id}...")
        
        reactions_list = ['👍', '❤️', '🔥', '👏', '😍']
        
        for account in available_accounts:
            client = await self.get_client_for_account(account)
            if not client:
                continue
            
            try:
                # 1. Join if needed
                entity = await self.join_channel(client, account['id'], order['channel_username'], order['id'])
                
                # 2. Get correct entity if join returned True or Entity is bool
                if isinstance(entity, bool) or entity is None:
                     try:
                        entity = await client.get_entity(order['channel_username'].replace('@', ''))
                     except:
                        continue

                # 3. Deliver
                if 'react' in order['plan_type']:
                    reaction = random.choice(reactions_list)
                    await client.send_reaction(entity, message.id, reaction)
                    action_type = 'reaction_delivery'
                else:
                    # DEBUG LOG
                    logger.info(f"Attempting view increment for msg {message.id} with account {account['id']}")
                    
                    # Correct View Logic using GetMessagesViewsRequest
                    await client(GetMessagesViewsRequest(
                        peer=entity,
                        id=[message.id],
                        increment=True
                    ))
                    action_type = 'view_delivery'
                
                self.db.update_account_last_used(account['id'])
                self.db.log_account_usage(account['id'], order['id'], order['channel_username'], action_type, True)
                
                await asyncio.sleep(delay_seconds) 
                
            except Exception as e:
                logger.error(f"Error delivering action with account {account['id']}: {e}")

    async def should_deliver_for_limited_plan(self, order):
        order_id = order['id']
        total_posts_for_plan = order['total_posts']
        delivered_posts_total = order.get('delivered_posts', 0)
        
        if delivered_posts_total >= total_posts_for_plan:
            logger.info(f"Order {order_id} reached TOTAL limit.")
            self.db.update_order_status(order_id, 'completed')
            return False
            
        daily_posts_limit = order['daily_posts_limit']
        daily_delivery_count = order.get('daily_delivery_count', 0)
        last_delivery_date = order.get('last_delivery_date')
        today = date.today()

        if last_delivery_date is None or last_delivery_date != today:
            self.db.reset_daily_delivery_count(order_id)
            daily_delivery_count = 0
        
        if daily_delivery_count >= daily_posts_limit:
            return False
            
        return True
    
    async def process_new_message_for_standard_plan(self, message, order):
        plan_type = order['plan_type']
        order_id = order['id']
        
        logger.info(f"Processing new message {message.id} in {order['channel_username']} for STANDARD order {order_id}")
        
        should_deliver = True
        if 'limited' in plan_type:
            should_deliver = await self.should_deliver_for_limited_plan(order)
            
        if should_deliver:
            await self.deliver_views_or_reactions(message, order)
            self.db.increment_delivered_posts(order_id)
            if 'limited' in plan_type:
                self.db.increment_daily_delivery_count(order_id)
    
    async def monitor_channel(self, channel_username, orders):
        logger.info(f"Starting to monitor channel: {channel_username}")
        
        client_to_use = None
        entity = None
        try:
            # Find a client already in the channel to act as the monitor
            for order in orders:
                log = self.db.connection.cursor()
                log.execute("""
                    SELECT sa.id, sa.session_string FROM account_usage_logs aul
                    JOIN sold_accounts sa ON aul.account_id = sa.id
                    WHERE aul.order_id = %s AND (aul.action_type LIKE '%%join%%')
                    LIMIT 1
                """, (order['id'],))
                account = log.fetchone()
                log.close()
                
                if account:
                    client_to_use = await self.get_client_for_account(account)
                    if client_to_use:
                        try:
                            if 'joinchat/' in channel_username or 't.me/+' in channel_username:
                                entity = await client_to_use.get_entity(channel_username)
                            else:
                                entity = await client_to_use.get_entity(channel_username.replace('@',''))
                            
                            if entity:
                                break
                        except Exception:
                            pass
            
            # Fallback: Just grab any active account and try to peek
            if not client_to_use:
                 acc = next(iter(self.db.get_available_accounts(limit=1)), None)
                 if acc:
                     client_to_use = await self.get_client_for_account(acc)

            if not client_to_use:
                logger.error(f"No clients available to monitor {channel_username}.")
                return

            @client_to_use.on(events.NewMessage(chats=entity))
            async def handle_new_message(event):
                message = event.message
                active_orders_for_channel = self.active_channels.get(channel_username, [])
                
                for order in active_orders_for_channel:
                    try:
                        fresh_order = self.db.get_order_by_id(order['id'])
                        if not fresh_order or fresh_order['status'] != 'active':
                            continue
                        
                        await self.process_new_message_for_standard_plan(message, fresh_order)
                    except Exception as e:
                        logger.error(f"Error processing message for order {order['id']}: {e}")
            
            logger.info(f"Successfully set up monitoring for {channel_username}")
            
            # Keep monitoring loop alive
            while channel_username in self.active_channels:
                await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error setting up monitoring for channel {channel_username}: {e}")
            if channel_username in self.active_channels:
                del self.active_channels[channel_username]
            self.monitored_orders = {o_id for o_id in self.monitored_orders if self.db.get_order_by_id(o_id)['channel_username'] != channel_username}
    
    # ---------------------------------------------------------
    # MAIN LOOP
    # ---------------------------------------------------------

    async def run(self):
        logger.info("Service Delivery Worker started")
        monitored_channels = set()
        
        while True:
            try:
                await self.process_new_orders()
                
                # Check for standard plans that need monitoring
                for channel_username in list(self.active_channels.keys()):
                    if channel_username not in monitored_channels:
                        orders = self.active_channels[channel_username]
                        asyncio.create_task(self.monitor_channel(channel_username, orders))
                        monitored_channels.add(channel_username)
                
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(10)

    async def process_new_orders(self):
        orders = self.db.get_active_orders()
        for order in orders:
            order_id = order['id']
            if order_id in self.monitored_orders: continue
            
            # Route to correct handler
            if 'join' in order['plan_type'] or order['duration'] == 0:
                self.monitored_orders.add(order_id)
                asyncio.create_task(self.execute_join_and_leave_order(order))
            
            elif order['duration'] > 0:
                # Standard Plan - Add to monitoring list
                channel = order['channel_username']
                if channel not in self.active_channels:
                    self.active_channels[channel] = []
                self.active_channels[channel].append(order)
                self.monitored_orders.add(order_id)
                
                # Update expiry if needed
                if not order.get('expires_at'):
                    expires_at = datetime.now() + timedelta(days=order.get('duration', 30))
                    self.db.update_order_expiry(order_id, expires_at)

async def main():
    if not os.path.exists('sessions'): os.makedirs('sessions')
    worker = ServiceDeliveryWorker()
    await worker.run()

if __name__ == '__main__':
    asyncio.run(main())