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
from telethon.tl.functions.messages import ImportChatInviteRequest
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from datetime import datetime, timedelta, date
import time
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ServiceDeliveryWorker:
    def __init__(self):
        self.db = Database()
        self.active_channels = {} # Stores standard, daily-monitoring plans
        self.active_clients = {}
        self.monitored_orders = set()

    async def create_client_from_session(self, account_id, session_string):
        """Create a Telethon client from a session string"""
        try:
            session_path = f"sessions/account_{account_id}.session"
            client = TelegramClient(
                session_path,
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH
            )
            await client.connect()
            
            if not await client.is_user_authorized():
                # If file session fails, try in-memory StringSession once
                logger.warning(f"File session for {account_id} failed. Trying StringSession.")
                client = TelegramClient(
                    StringSession(session_string),
                    TELEGRAM_API_ID,
                    TELEGRAM_API_HASH
                )
                await client.connect()
                
                if not await client.is_user_authorized():
                    logger.error(f"Account {account_id} session is not authorized")
                    self.db.update_account_status(account_id, 'banned', is_banned=True)
                    return None
            
            if not os.path.exists('sessions'):
                os.makedirs('sessions')
            if not os.path.exists(session_path):
                 with open(session_path, 'w') as f:
                    f.write(client.session.save())

            return client
        except Exception as e:
            logger.error(f"Error creating client for account {account_id}: {e}")
            return None

    async def get_client_for_account(self, account):
        """Gets a client, creating one if not already active."""
        account_id = account['id']
        session_string = account['session_string']

        if account_id in self.active_clients:
            client = self.active_clients[account_id]
            try:
                if client.is_connected() or await client.connect():
                    if await client.is_user_authorized():
                        return client
            except Exception as e:
                logger.error(f"Reconnecting client {account_id} failed: {e}")

        client = await self.create_client_from_session(account_id, session_string)
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
            logger.warning(f"Flood wait error for account {account_id}: must wait {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return None
        except Exception as e:
            if "already a participant" in str(e).lower():
                logger.warning(f"Account {account_id} already in channel {channel_username}")
                try:
                    if 'joinchat/' in channel_username or 't.me/+' in channel_username:
                        return True 
                    return await client.get_entity(channel_username.replace('@',''))
                except Exception:
                    return True 
            logger.error(f"Error joining channel {channel_username} with account {account_id}: {e}")
            return None

    async def execute_join_and_leave_order(self, order):
        """
        Handles the entire lifecycle of a one-time "Join & Leave" order.
        """
        order_id = order['id']
        plan_type = order['plan_type']
        channel_username = order['channel_username']
        post_count = order['total_posts'] 
        quantity = order['views_per_post'] 
        delay_seconds = order.get('delay_seconds', 1)
        is_reaction = 'react' in plan_type
        
        logger.info(f"Executing NEW Join & Leave Order #{order_id} for {channel_username}")
        
        channel_entity = None
        clients_in_job = {}
        try:
            available_accounts = self.db.get_available_accounts(limit=quantity)
            if len(available_accounts) == 0:
                logger.error(f"Order #{order_id}: No accounts available in pool. Need {quantity}. Aborting.")
                self.db.update_order_status(order_id, 'failed')
                return
                
            if len(available_accounts) < quantity:
                logger.warning(f"Order #{order_id}: Not enough accounts. Need {quantity}, have {len(available_accounts)}")
            
            monitor_client = None

            logger.info(f"Order #{order_id}: Joining channel with {len(available_accounts)} accounts...")
            joined_count = 0
            for account in available_accounts:
                client = await self.get_client_for_account(account)
                if not client:
                    continue
                
                if not monitor_client:
                    monitor_client = client

                entity = await self.join_channel(client, account['id'], channel_username, order_id)
                if entity:
                    clients_in_job[account['id']] = client
                    joined_count += 1
                    if not channel_entity:
                        channel_entity = entity
                
                await asyncio.sleep(random.uniform(1, 3)) 

            if joined_count == 0 or not monitor_client or not channel_entity:
                logger.error(f"Order #{order_id}: No accounts could join channel {channel_username}. Aborting.")
                self.db.update_order_status(order_id, 'failed')
                return

            logger.info(f"Order #{order_id}: Successfully joined with {joined_count} accounts. Getting posts...")

            messages = await monitor_client.get_messages(channel_entity, limit=post_count)

            if not messages:
                logger.warning(f"Order #{order_id}: No posts found in channel {channel_username}.")
            else:
                logger.info(f"Order #{order_id}: Found {len(messages)} posts to service.")
                
                reactions_list = ['👍', '❤️', '🔥', '👏', '😍', '🎉', '🤩']
                
                for post in messages:
                    logger.info(f"Order #{order_id}: Servicing post {post.id}...")
                    delivered_count = 0
                    
                    for account_id, client in clients_in_job.items():
                        try:
                            if is_reaction:
                                reaction = random.choice(reactions_list)
                                await client.send_reaction(post.chat_id, post.id, reaction)
                                action_type = 'reaction_delivery'
                            else:
                                await client.send_read_acknowledge(post.chat_id, post.id)
                                action_type = 'view_delivery'
                            
                            self.db.log_account_usage(account_id, order_id, channel_username, action_type, True)
                            delivered_count += 1
                            await asyncio.sleep(delay_seconds)
                        
                        except Exception as e:
                            logger.warning(f"Order #{order_id}: Account {account_id} failed to service post {post.id}: {e}")

                    logger.info(f"Order #{order_id}: Delivered {delivered_count} services to post {post.id}")
                    self.db.increment_delivered_posts(order_id)
                    await asyncio.sleep(random.uniform(5, 15))

            logger.info(f"Order #{order_id}: Service complete. Leaving channel...")
            for account_id, client in clients_in_job.items():
                try:
                    await client(LeaveChannelRequest(channel_entity))
                    self.db.log_account_usage(account_id, order_id, channel_username, 'channel_leave', True)
                    self.db.decrement_account_join_count(account_id)
                except Exception as e:
                    logger.error(f"Order #{order_id}: Account {account_id} failed to leave: {e}")

            self.db.update_order_status(order_id, 'completed')
            logger.info(f"🎉 Order #{order_id} (Join & Leave) is marked as COMPLETED.")
            
        except Exception as e:
            logger.error(f"CRITICAL: Failed to execute Join & Leave Order #{order_id}: {e}")
            self.db.update_order_status(order_id, 'failed')
        finally:
            for account_id, client in clients_in_job.items():
                if client and client.is_connected():
                    await client.disconnect()
                if account_id in self.active_clients:
                    del self.active_clients[account_id]


    async def process_new_orders(self):
        active_orders = self.db.get_active_orders()
        
        for order in active_orders:
            order_id = order['id']
            plan_type = order['plan_type']

            if order_id in self.monitored_orders:
                continue

            if 'join' in plan_type or order['duration'] == 0:
                logger.info(f"Found new Join & Leave order #{order_id}. Starting one-time job.")
                self.monitored_orders.add(order_id)
                asyncio.create_task(self.execute_join_and_leave_order(order))
            
            elif order['duration'] > 0:
                channel_username = order['channel_username']
                logger.info(f"New active Standard order {order_id} detected for channel {channel_username}")
                
                account = next(iter(self.db.get_available_accounts(limit=1)), None)
                if not account:
                    logger.error(f"Order #{order_id}: No accounts available in pool to monitor channel. Skipping.")
                    continue
                
                client = await self.get_client_for_account(account)
                if not client:
                    logger.error(f"Order #{order_id}: Could not create client for monitoring. Skipping.")
                    continue
                
                entity = await self.join_channel(client, account['id'], channel_username, order_id)
                
                if entity:
                    self.monitored_orders.add(order_id)
                    if channel_username not in self.active_channels:
                        self.active_channels[channel_username] = []
                    self.active_channels[channel_username].append(order)
                    
                    if not order.get('expires_at'):
                        duration_days = order.get('duration', 30)
                        expires_at = datetime.now() + timedelta(days=duration_days)
                        self.db.update_order_expiry(order_id, expires_at)
                else:
                    logger.warning(f"Order #{order_id}: Failed to join channel {channel_username} for monitoring.")
            
            else:
                logger.error(f"Order #{order_id}: Unknown plan type. Skipping.")
                self.monitored_orders.add(order_id)

    async def deliver_views(self, message, order):
        account_count = order['views_per_post']
        delay_seconds = order.get('delay_seconds', 10) 
        available_accounts = self.db.get_available_accounts(limit=account_count)
        
        logger.info(f"Order #{order['id']}: Delivering {len(available_accounts)} views to post {message.id}...")
        
        for account in available_accounts:
            client = await self.get_client_for_account(account)
            if not client:
                continue
            
            try:
                await self.join_channel(client, account['id'], order['channel_username'], order['id'])
                await client.send_read_acknowledge(message.chat_id, message.id)
                self.db.update_account_last_used(account['id'])
                self.db.log_account_usage(account['id'], order['id'], order['channel_username'], 'view_delivery', True)
                await asyncio.sleep(delay_seconds) 
                
            except Exception as e:
                logger.error(f"Error delivering view with account {account['id']}: {e}")

    async def deliver_reactions(self, message, order):
        account_count = order['views_per_post']
        delay_seconds = order.get('delay_seconds', 10) 
        available_accounts = self.db.get_available_accounts(limit=account_count)
        
        logger.info(f"Order #{order['id']}: Delivering {len(available_accounts)} reactions to post {message.id}...")
        reactions = ['👍', '❤️', '🔥', '👏', '😍']
        
        for idx, account in enumerate(available_accounts):
            client = await self.get_client_for_account(account)
            if not client:
                continue
                
            try:
                await self.join_channel(client, account['id'], order['channel_username'], order['id'])
                reaction = reactions[idx % len(reactions)]
                await client.send_reaction(message.chat_id, message.id, reaction)
                self.db.update_account_last_used(account['id'])
                self.db.log_account_usage(account['id'], order['id'], order['channel_username'], 'reaction_delivery', True)
                await asyncio.sleep(delay_seconds) 
                
            except Exception as e:
                logger.error(f"Error delivering reaction with account {account['id']}: {e}")
        
    async def should_deliver_for_limited_plan(self, order):
        order_id = order['id']
        
        total_posts_for_plan = order['total_posts']
        delivered_posts_total = order.get('delivered_posts', 0)
        
        if delivered_posts_total >= total_posts_for_plan:
            logger.info(f"Order {order_id} has reached its TOTAL post limit ({delivered_posts_total}/{total_posts_for_plan})")
            self.db.update_order_status(order_id, 'completed')
            return False
            
        daily_posts_limit = order['daily_posts_limit']
        daily_delivery_count = order.get('daily_delivery_count', 0)
        last_delivery_date = order.get('last_delivery_date')
        today = date.today()

        if last_delivery_date is None or last_delivery_date != today:
            logger.info(f"Order {order_id}: New day. Resetting daily delivery count to 0.")
            self.db.reset_daily_delivery_count(order_id)
            daily_delivery_count = 0
        
        if daily_delivery_count >= daily_posts_limit:
            logger.info(f"Order {order_id} has reached its DAILY post limit for {today} ({daily_delivery_count}/{daily_posts_limit})")
            return False
            
        return True
    
    async def process_new_message_for_standard_plan(self, message, order):
        plan_type = order['plan_type']
        order_id = order['id']
        
        logger.info(f"Processing new message {message.id} in {order['channel_username']} for STANDARD order {order_id}")
        
        if 'unlimited' in plan_type:
            if 'view' in plan_type:
                await self.deliver_views(message, order)
            else:
                await self.deliver_reactions(message, order)
            self.db.increment_delivered_posts(order_id) 
            
        elif 'limited' in plan_type:
            if await self.should_deliver_for_limited_plan(order):
                if 'view' in plan_type:
                    await self.deliver_views(message, order)
                else:
                    await self.deliver_reactions(message, order)
                
                self.db.increment_delivered_posts(order_id)
                self.db.increment_daily_delivery_count(order_id)
    
    async def monitor_channel(self, channel_username, orders):
        logger.info(f"Starting to monitor channel: {channel_username}")
        
        client_to_use = None
        entity = None
        try:
            for order in orders:
                log = self.db.connection.cursor()
                log.execute("""
                    SELECT sa.id, sa.session_string FROM account_usage_logs aul
                    JOIN sold_accounts sa ON aul.account_id = sa.id
                    WHERE aul.order_id = %s AND (aul.action_type LIKE '%%join%%' OR aul.action_type = 'view_delivery')
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
                        except Exception as e:
                            logger.warning(f"Monitor client setup for {channel_username} failed with one account, trying next. Error: {e}")
            
            if not client_to_use or not entity:
                logger.error(f"No active clients/entity available to monitor {channel_username}. Will retry.")
                if channel_username in self.active_channels:
                    del self.active_channels[channel_username]
                self.monitored_orders = {o_id for o_id in self.monitored_orders if self.db.get_order_by_id(o_id)['channel_username'] != channel_username}
                return

            from telethon import events
            
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
            
        except Exception as e:
            logger.error(f"Error setting up monitoring for channel {channel_username}: {e}")
            if channel_username in self.active_channels:
                del self.active_channels[channel_username]
            self.monitored_orders = {o_id for o_id in self.monitored_orders if self.db.get_order_by_id(o_id)['channel_username'] != channel_username}
    
    async def run(self):
        """Main worker loop"""
        logger.info("Service Delivery Worker started")
        
        monitored_channels = set()
        
        while True:
            try:
                await self.process_new_orders()
                
                for channel_username in list(self.active_channels.keys()):
                    if channel_username not in monitored_channels:
                        orders = self.active_channels[channel_username]
                        asyncio.create_task(self.monitor_channel(channel_username, orders))
                        monitored_channels.add(channel_username)
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(60)
    
    async def cleanup(self):
        """Cleanup: disconnect all clients"""
        logger.info("Cleaning up worker...")
        for account_id, client in self.active_clients.items():
            try:
                if client.is_connected():
                    await client.disconnect()
            except:
                pass
        logger.info("Worker cleanup complete")

async def main():
    if not os.path.exists('sessions'):
        os.makedirs('sessions')
        
    worker = ServiceDeliveryWorker()
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    finally:
        await worker.cleanup()

if __name__ == '__main__':
    asyncio.run(main())