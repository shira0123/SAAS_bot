import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import ChannelPrivateError, UserBannedInChannelError, FloodWaitError, InviteHashExpiredError
from telethon.tl.functions.channels import JoinChannelRequest
from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH
from datetime import datetime, timedelta
import time

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
        """Create a Telethon client from a session string"""
        try:
            client = TelegramClient(
                StringSession(session_string),
                TELEGRAM_API_ID,
                TELEGRAM_API_HASH
            )
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error(f"Account {account_id} session is not authorized")
                return None
            
            return client
        except Exception as e:
            logger.error(f"Error creating client for account {account_id}: {e}")
            return None
    
    async def join_channel(self, client, account_id, channel_username, order_id):
        """Make an account join a channel (public or private)"""
        try:
            channel_username = channel_username.strip().replace('@', '')
            if channel_username.startswith('https://') or channel_username.startswith('t.me/'):
                channel_username = channel_username.split('/')[-1]
            
            try:
                entity = await client.get_entity(channel_username)
                
                await client(JoinChannelRequest(entity))
                
                self.db.increment_account_join_count(account_id)
                self.db.log_account_usage(
                    account_id, order_id, channel_username, 
                    'channel_join', success=True
                )
                
                logger.info(f"Account {account_id} successfully joined channel {channel_username}")
                return True
                
            except ChannelPrivateError:
                logger.warning(f"Channel {channel_username} is private, sending join request")
                try:
                    entity = await client.get_entity(channel_username)
                    await client(JoinChannelRequest(entity))
                    
                    self.db.log_account_usage(
                        account_id, order_id, channel_username,
                        'private_channel_join_request', success=True
                    )
                    logger.info(f"Account {account_id} sent join request to private channel {channel_username}")
                    return True
                except Exception as e:
                    logger.error(f"Error requesting to join private channel {channel_username}: {e}")
                    return False
                    
        except UserBannedInChannelError:
            logger.error(f"Account {account_id} is banned in channel {channel_username}")
            self.db.update_account_status(account_id, 'banned', is_banned=True)
            self.db.log_account_usage(
                account_id, order_id, channel_username,
                'channel_join', success=False, error_message='Account banned in channel'
            )
            return False
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait error for account {account_id}: must wait {e.seconds} seconds")
            self.db.log_account_usage(
                account_id, order_id, channel_username,
                'channel_join', success=False, error_message=f'Flood wait: {e.seconds}s'
            )
            await asyncio.sleep(e.seconds)
            return False
            
        except Exception as e:
            logger.error(f"Error joining channel {channel_username} with account {account_id}: {e}")
            self.db.log_account_usage(
                account_id, order_id, channel_username,
                'channel_join', success=False, error_message=str(e)
            )
            return False
    
    async def join_channel_with_accounts(self, channel_username, order_id, num_accounts):
        """Join a channel with multiple accounts from the pool"""
        available_accounts = self.db.get_available_accounts(limit=num_accounts)
        
        if len(available_accounts) < num_accounts:
            logger.warning(f"Only {len(available_accounts)} available accounts, need {num_accounts}")
        
        join_tasks = []
        successful_joins = 0
        
        for account in available_accounts[:num_accounts]:
            account_id = account['id']
            session_string = account['session_string']
            
            try:
                client = await self.create_client_from_session(account_id, session_string)
                
                if client:
                    self.active_clients[account_id] = client
                    success = await self.join_channel(client, account_id, channel_username, order_id)
                    
                    if success:
                        successful_joins += 1
                    
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error processing account {account_id}: {e}")
                continue
        
        logger.info(f"Joined channel {channel_username} with {successful_joins}/{num_accounts} accounts")
        return successful_joins
    
    async def process_new_orders(self):
        """Check for new active orders and join their channels"""
        active_orders = self.db.get_active_orders()
        
        for order in active_orders:
            order_id = order['id']
            
            if order_id in self.monitored_orders:
                continue
            
            channel_username = order['channel_username']
            views_per_post = order['views_per_post']
            
            logger.info(f"New active order {order_id} detected for channel {channel_username}")
            
            await self.join_channel_with_accounts(channel_username, order_id, views_per_post)
            
            self.monitored_orders.add(order_id)
            self.active_channels[channel_username] = order
            
            if not order.get('expires_at'):
                duration_days = order.get('duration', 30)
                expires_at = datetime.now() + timedelta(days=duration_days)
                self.db.update_order_expiry(order_id, expires_at)
                logger.info(f"Set expiry for order {order_id} to {expires_at}")
    
    async def deliver_views(self, message, order, delay_seconds=10):
        """Deliver views to a message"""
        account_count = order['views_per_post']
        available_accounts = self.db.get_available_accounts(limit=account_count)
        
        if len(available_accounts) < account_count:
            logger.warning(f"Only {len(available_accounts)} accounts available for order {order['id']}, need {account_count}")
        
        successful_views = 0
        
        for account in available_accounts:
            account_id = account['id']
            session_string = account['session_string']
            
            try:
                if account_id not in self.active_clients:
                    client = await self.create_client_from_session(account_id, session_string)
                    if client:
                        self.active_clients[account_id] = client
                    else:
                        continue
                else:
                    client = self.active_clients[account_id]
                
                await client.send_read_acknowledge(message.chat_id, message.id)
                
                self.db.update_account_last_used(account_id)
                self.db.log_account_usage(
                    account_id, order['id'], order['channel_username'],
                    'view_delivery', success=True
                )
                successful_views += 1
                
                await asyncio.sleep(delay_seconds)
                
            except Exception as e:
                logger.error(f"Error delivering view with account {account_id}: {e}")
                self.db.log_account_usage(
                    account_id, order['id'], order['channel_username'],
                    'view_delivery', success=False, error_message=str(e)
                )
                continue
        
        logger.info(f"Delivered {successful_views} views for message {message.id} in {order['channel_username']}")
        return successful_views
    
    async def deliver_reactions(self, message, order, delay_seconds=10):
        """Deliver reactions to a message"""
        account_count = order['views_per_post']
        available_accounts = self.db.get_available_accounts(limit=account_count)
        
        if len(available_accounts) < account_count:
            logger.warning(f"Only {len(available_accounts)} accounts available for order {order['id']}, need {account_count}")
        
        successful_reactions = 0
        reactions = ['👍', '❤️', '🔥', '👏', '😍']
        
        for idx, account in enumerate(available_accounts):
            account_id = account['id']
            session_string = account['session_string']
            
            try:
                if account_id not in self.active_clients:
                    client = await self.create_client_from_session(account_id, session_string)
                    if client:
                        self.active_clients[account_id] = client
                    else:
                        continue
                else:
                    client = self.active_clients[account_id]
                
                reaction = reactions[idx % len(reactions)]
                await client.send_reaction(message.chat_id, message.id, reaction)
                
                self.db.update_account_last_used(account_id)
                self.db.log_account_usage(
                    account_id, order['id'], order['channel_username'],
                    'reaction_delivery', success=True
                )
                successful_reactions += 1
                
                await asyncio.sleep(delay_seconds)
                
            except Exception as e:
                logger.error(f"Error delivering reaction with account {account_id}: {e}")
                self.db.log_account_usage(
                    account_id, order['id'], order['channel_username'],
                    'reaction_delivery', success=False, error_message=str(e)
                )
                continue
        
        logger.info(f"Delivered {successful_reactions} reactions for message {message.id} in {order['channel_username']}")
        return successful_reactions
    
    async def should_deliver_for_limited_plan(self, order):
        """Check if we should deliver for a limited plan based on daily quota"""
        total_posts = order['total_posts']
        delivered_posts = order.get('delivered_posts', 0)
        
        if delivered_posts >= total_posts:
            logger.info(f"Order {order['id']} has reached daily post limit ({delivered_posts}/{total_posts})")
            return False
        
        return True
    
    async def process_new_message(self, message, order):
        """Process a new message/post for an order"""
        plan_type = order['plan_type']
        delay_seconds = order.get('delay_seconds', 10)
        
        logger.info(f"Processing new message {message.id} in {order['channel_username']} for order {order['id']}")
        
        if 'unlimited_views' in plan_type:
            await self.deliver_views(message, order, delay_seconds)
            
        elif 'limited_views' in plan_type:
            if await self.should_deliver_for_limited_plan(order):
                await self.deliver_views(message, order, delay_seconds)
                new_count = self.db.increment_delivered_posts(order['id'])
                order['delivered_posts'] = new_count
            
        elif 'unlimited_reactions' in plan_type:
            await self.deliver_reactions(message, order, delay_seconds)
            
        elif 'limited_reactions' in plan_type:
            if await self.should_deliver_for_limited_plan(order):
                await self.deliver_reactions(message, order, delay_seconds)
                new_count = self.db.increment_delivered_posts(order['id'])
                order['delivered_posts'] = new_count
    
    async def monitor_channel(self, channel_username, orders):
        """Monitor a specific channel for new posts and deliver services"""
        logger.info(f"Starting to monitor channel: {channel_username}")
        
        try:
            if not self.active_clients:
                logger.error("No active clients available for monitoring")
                return
            
            monitor_client = list(self.active_clients.values())[0]
            
            entity = await monitor_client.get_entity(channel_username)
            
            from telethon import events
            
            @monitor_client.on(events.NewMessage(chats=entity))
            async def handle_new_message(event):
                message = event.message
                
                for order in orders:
                    try:
                        await self.process_new_message(message, order)
                    except Exception as e:
                        logger.error(f"Error processing message for order {order['id']}: {e}")
            
            logger.info(f"Successfully set up monitoring for {channel_username}")
            
        except Exception as e:
            logger.error(f"Error setting up monitoring for channel {channel_username}: {e}")
    
    async def check_expired_orders(self):
        """Check for expired orders (Phase 8.4)"""
        logger.info("Expiry checking will be implemented in Phase 8.4")
        pass
    
    async def run(self):
        """Main worker loop"""
        logger.info("Service Delivery Worker started")
        
        while True:
            try:
                await self.process_new_orders()
                
                for channel_username, orders in self.active_channels.items():
                    if isinstance(orders, dict):
                        orders = [orders]
                    await self.monitor_channel(channel_username, orders)
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(60)
    
    async def cleanup(self):
        """Cleanup: disconnect all clients"""
        logger.info("Cleaning up worker...")
        for account_id, client in self.active_clients.items():
            try:
                await client.disconnect()
            except:
                pass
        logger.info("Worker cleanup complete")

async def main():
    worker = ServiceDeliveryWorker()
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    finally:
        await worker.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
