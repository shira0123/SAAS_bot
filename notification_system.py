import logging
from telegram import Bot
from telegram.ext import ContextTypes
from config import BOT_TOKEN, ADMIN_IDS
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

async def notify_admins_new_deposit(context: ContextTypes.DEFAULT_TYPE, user_id, amount, gateway):
    """Notify admins of new deposit request"""
    try:
        user = db.get_user(user_id)
        username = user.get('username', 'N/A') if user else 'N/A'
        name = user.get('first_name', 'Unknown') if user else 'Unknown'
        
        message = f"""
🔔 **New Deposit Request**

**Gateway:** {gateway}
**User:** {name} (@{username})
**Amount:** ${amount:.2f}
**User ID:** {user_id}

Use /deposits to verify.
"""
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in notify_admins_new_deposit: {e}")

async def notify_admins_new_plan_purchase(context: ContextTypes.DEFAULT_TYPE, user_id, order_id, plan_type, amount):
    """Notify admins of new plan purchase"""
    try:
        user = db.get_user(user_id)
        username = user.get('username', 'N/A') if user else 'N/A'
        
        message = f"""
🎉 **New Plan Purchase**

**Order ID:** #{order_id}
**User:** @{username}
**Plan:** {plan_type.replace('_', ' ').title()}
**Amount:** ${amount:.2f}
"""
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in notify_admins_new_plan_purchase: {e}")

async def notify_admins_referral_sale(context: ContextTypes.DEFAULT_TYPE, referrer_id, referred_id, commission):
    """Notify admins of referral commission earned"""
    try:
        referrer = db.get_user(referrer_id)
        referred = db.get_user(referred_id)
        
        message = f"""
💰 **Referral Commission Earned**

**Referrer:** @{referrer.get('username', 'N/A')}
**Referred User:** @{referred.get('username', 'N/A')}
**Commission:** ${commission:.2f}
"""
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in notify_admins_referral_sale: {e}")

async def notify_admins_reseller_sale(context: ContextTypes.DEFAULT_TYPE, reseller_id, order_id, profit):
    """Notify admins of reseller sale"""
    try:
        reseller = db.get_user(reseller_id)
        
        message = f"""
👔 **Reseller Sale**

**Reseller:** @{reseller.get('username', 'N/A')}
**Order ID:** #{order_id}
**Profit:** ${profit:.2f}
"""
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error in notify_admins_reseller_sale: {e}")

async def notify_user_referral_commission(context: ContextTypes.DEFAULT_TYPE, user_id, commission, referred_username):
    """Notify user they earned referral commission"""
    try:
        user = db.get_user(user_id)
        new_balance = user.get('buyer_referral_balance', 0) if user else 0
        
        message = f"""
🎉 **You Earned a Commission!**

Your referral @{referred_username} made a purchase!

**Commission Earned:** ${commission:.2f}
**New Referral Balance:** ${new_balance:.2f}

Keep sharing your referral link to earn more! 💰
"""
        
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying user {user_id} of commission: {e}")

async def notify_user_referral_withdrawal_approved(context: ContextTypes.DEFAULT_TYPE, user_id, amount):
    """Notify user their referral withdrawal was approved"""
    try:
        message = f"""
✅ **Withdrawal Approved!**

Your referral commission withdrawal has been approved and processed.

**Amount:** ${amount:.2f}

Thank you for promoting our service! 🎉
"""
        
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")

async def notify_reseller_new_order(context: ContextTypes.DEFAULT_TYPE, reseller_id, order_id, profit):
    """Notify reseller of new order via their link"""
    try:
        message = f"""
🎉 **New Sale Through Your Link!**

**Order ID:** #{order_id}
**Your Profit:** ${profit:.2f}

Keep sharing your reseller links! 👔
"""
        
        await context.bot.send_message(chat_id=reseller_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying reseller {reseller_id}: {e}")

async def notify_reseller_withdrawal_approved(context: ContextTypes.DEFAULT_TYPE, user_id, amount):
    """Notify reseller their commission withdrawal was approved"""
    try:
        message = f"""
✅ **Commission Withdrawal Approved!**

Your reseller commission withdrawal has been processed.

**Amount:** ${amount:.2f}

Thank you for being a valued reseller! 🎉
"""
        
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying reseller {user_id}: {e}")

async def notify_user_payment_success(context: ContextTypes.DEFAULT_TYPE, user_id, amount, method):
    """Notify user of successful payment"""
    try:
        user = db.get_user(user_id)
        new_balance = user.get('buyer_wallet_balance', 0) if user else 0
        
        message = f"""
✅ **Payment Successful!**

Your payment has been confirmed.

**Amount:** ${amount:.2f}
**Method:** {method}
**New Balance:** ${new_balance:.2f}

You can now purchase plans! 💎
"""
        
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")

async def notify_user_plan_activated(context: ContextTypes.DEFAULT_TYPE, user_id, order_id, plan_type):
    """Notify user their plan is now active"""
    try:
        message = f"""
🎉 **Plan Activated!**

**Order ID:** #{order_id}
**Plan:** {plan_type.replace('_', ' ').title()}

Your service is now active and will begin shortly!
"""
        
        await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")
