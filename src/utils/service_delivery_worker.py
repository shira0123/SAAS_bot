import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import asyncio
import logging
import random
from datetime import datetime, date

from pyrogram import Client, filters, handlers
from pyrogram.raw.functions.messages import GetMessagesViews
from pyrogram.raw.types import UpdateNewChannelMessage, Message as RawMessage
from pyrogram.errors import (
    UserBannedInChannel, FloodWait, UserAlreadyParticipant, PeerIdInvalid,
    UserDeactivated, AuthKeyUnregistered, SessionRevoked, UserDeactivatedBan
)

from src.database.database import Database
from src.database.config import TELEGRAM_API_ID, TELEGRAM_API_HASH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceDeliveryWorker:
    def __init__(self):
        self.db = Database()
        self.monitored_orders = set()
        self.active_monitors = {}     # channel_username -> watcher client
        self.prejoined_orders = set() # orders already prejoined

    # ---------------- CLIENT ---------------- #

    async def get_client(self, account, is_watcher=False):
        try:
            client = Client(
                name=f"{'w' if is_watcher else 'd'}_{account['id']}",
                api_id=int(TELEGRAM_API_ID),
                api_hash=TELEGRAM_API_HASH,
                session_string=account['session_string'],
                in_memory=True,
                no_updates=not is_watcher
            )

            if is_watcher:
                await client.start()
            else:
                await client.connect()

            return client

        except (UserDeactivated, AuthKeyUnregistered, SessionRevoked, UserDeactivatedBan):
            logger.error(f"❌ Account {account['id']} DEAD. Marking banned.")
            self.db.update_account_status(account['id'], 'banned', True)
            return None
        except Exception as e:
            logger.error(f"Client error acc {account['id']}: {e}")
            return None

    # ---------------- JOIN ---------------- #

    async def join_channel(self, client, account_id, channel_username, order_id=None):
        try:
            chat = await client.join_chat(channel_username)
            if order_id:
                self.db.increment_account_join_count(account_id)
                self.db.log_account_usage(account_id, order_id, channel_username, 'join', True)
            return chat

        except UserAlreadyParticipant:
            try:
                return await client.get_chat(channel_username)
            except Exception:
                return None

        except UserBannedInChannel:
            self.db.update_account_status(account_id, 'banned', True)
            return None

        except FloodWait as e:
            logger.warning(f"FloodWait {e.value}s for acc {account_id}")
            await asyncio.sleep(e.value + 1)
            return None

        except Exception as e:
            logger.error(f"Join error: {e}")
            return None

    # ---------------- PREJOIN (NEW – CORE FIX) ---------------- #

    async def prejoin_accounts_for_plan(self, order):
        """
        SaaS Rule:
        Unlimited & Limited plans must pre-join ALL worker accounts immediately.
        """
        order_id = order['id']
        channel = order['channel_username']
        target = order['views_per_post']

        logger.info(f"🔗 Prejoining accounts for Order #{order_id}")

        accounts = self.db.get_available_accounts(limit=target)

        for acc in accounts:
            client = await self.get_client(acc, is_watcher=False)
            if not client:
                continue

            try:
                await self.join_channel(client, acc['id'], channel, order_id)
            except Exception as e:
                logger.error(f"Prejoin failed acc {acc['id']}: {e}")
            finally:
                await client.disconnect()

        self.prejoined_orders.add(order_id)
        logger.info(f"✅ Prejoin completed for Order #{order_id}")

    # ---------------- VIEWS DELIVERY ---------------- #

    async def deliver_views(self, client, chat_id, message_ids):
        try:
            peer = await client.resolve_peer(chat_id)
            await client.invoke(
                GetMessagesViews(peer=peer, id=message_ids, increment=True)
            )
            return True

        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            return False
        except Exception as e:
            logger.error(f"View error on chat {chat_id}: {e}")
            return False

    # ---------------- AUTO DELIVERY ---------------- #

    async def deliver_to_new_post(self, order_id, message_id, chat_id):
        order = self.db.get_order_by_id(order_id)
        if not order or order['status'] != 'active':
            return

        if 'limited' in order['plan_type']:
            if order['daily_delivery_count'] >= order['daily_posts_limit']:
                logger.info(f"🚫 Quota reached for Order #{order_id}")
                return

        logger.info(f"⚡ Starting delivery for Order #{order_id} on post {message_id}")

        accounts = self.db.get_available_accounts(limit=order['views_per_post'])
        success = 0

        for acc in accounts:
            client = await self.get_client(acc, is_watcher=False)
            if not client:
                continue

            try:
                if 'react' in order['plan_type']:
                    emoji = random.choice(['👍', '❤️', '🔥', '👏'])
                    await client.send_reaction(chat_id, message_id, emoji)
                else:
                    await self.deliver_views(client, chat_id, [message_id])

                success += 1
                self.db.log_account_usage(
                    acc['id'], order_id,
                    order['channel_username'],
                    'auto_deliver', True
                )
                await asyncio.sleep(order.get('delay_seconds', 1))

            except Exception as e:
                logger.error(f"Auto-delivery error: {e}")
            finally:
                await client.disconnect()

        if success:
            self.db.increment_delivered_posts(order_id)
            if 'limited' in order['plan_type']:
                self.db.increment_daily_delivery_count(order_id)

            logger.info(f"✅ Finished delivery for Order #{order_id} ({success} actions)")

    # ---------------- WATCHER ---------------- #

    async def start_channel_monitor(self, channel_username, order):
        if channel_username in self.active_monitors:
            return

        logger.info(f"👀 Starting watcher for {channel_username}")

        accounts = self.db.get_available_accounts(limit=5)

        for acc in accounts:
            client = await self.get_client(acc, is_watcher=True)
            if not client:
                continue

            try:
                chat = await client.join_chat(channel_username)
                chat_id = chat.id

                async def raw_handler(_, update, users, chats):
                    if not isinstance(update, UpdateNewChannelMessage):
                        return

                    msg: RawMessage = update.message
                    full_chat_id = -100 * msg.peer_id.channel_id
                    if full_chat_id != chat_id:
                        return

                    logger.info(f"📢 NEW POST DETECTED | ID: {msg.id} in {channel_username}")
                    for o in self.db.get_active_orders():
                        if o['channel_username'] == channel_username:
                            asyncio.create_task(
                                self.deliver_to_new_post(o['id'], msg.id, chat_id)
                            )

                client.add_handler(handlers.RawUpdateHandler(raw_handler))
                self.active_monitors[channel_username] = client

                logger.info(f"✅ Watcher ACTIVE for {channel_username}")
                return

            except Exception as e:
                logger.error(f"Watcher setup failed acc {acc['id']}: {e}")
                try:
                    await client.stop()
                except Exception:
                    pass

    # ---------------- JOIN & LEAVE ORDERS (UNCHANGED) ---------------- #

    async def execute_join_and_leave_order(self, order):
        order_id = order['id']
        channel = order['channel_username']
        target = order['views_per_post']

        logger.info(f"🚀 Processing Join/Leave Order #{order_id}")

        accounts = self.db.get_available_accounts(limit=target + 5)
        active_clients = []
        resolved_chat_id = None

        for acc in accounts:
            if len(active_clients) >= target:
                break

            client = await self.get_client(acc, is_watcher=False)
            if not client:
                continue

            chat = await self.join_channel(client, acc['id'], channel, order_id)
            if chat:
                resolved_chat_id = chat.id
                active_clients.append((acc['id'], client))
            else:
                await client.disconnect()

        if not active_clients or not resolved_chat_id:
            self.db.update_order_status(order_id, 'failed')
            return

        try:
            monitor_client = active_clients[0][1]
            message_ids = []

            async for msg in monitor_client.get_chat_history(
                resolved_chat_id,
                limit=order['total_posts']
            ):
                message_ids.append(msg.id)

            for acc_id, client in active_clients:
                try:
                    if 'react' in order['plan_type']:
                        for mid in message_ids:
                            emoji = random.choice(['👍', '❤️', '🔥', '👏'])
                            await client.send_reaction(resolved_chat_id, mid, emoji)
                    else:
                        await self.deliver_views(client, resolved_chat_id, message_ids)

                    self.db.log_account_usage(acc_id, order_id, channel, 'deliver', True)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Delivery phase error: {e}")

        for acc_id, client in active_clients:
            try:
                await client.leave_chat(resolved_chat_id)
                self.db.decrement_account_join_count(acc_id)
            except Exception:
                pass
            finally:
                await client.disconnect()

        self.db.update_order_status(order_id, 'completed')

    # ---------------- MAIN LOOP ---------------- #

    async def run(self):
        logger.info("Service Delivery Worker Started")

        while True:
            try:
                orders = self.db.get_active_orders()

                for order in orders:

                    # Join & Leave plans
                    if ('join' in order['plan_type'] or order['duration'] == 0):
                        if order['id'] not in self.monitored_orders:
                            self.monitored_orders.add(order['id'])
                            asyncio.create_task(self.execute_join_and_leave_order(order))

                    # Unlimited / Limited plans
                    else:
                        if order['id'] not in self.prejoined_orders:
                            await self.prejoin_accounts_for_plan(order)

                        if order['channel_username'] not in self.active_monitors:
                            asyncio.create_task(
                                self.start_channel_monitor(
                                    order['channel_username'], order
                                )
                            )

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Worker Loop Error: {e}")
                await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(ServiceDeliveryWorker().run())
