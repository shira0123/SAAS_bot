import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

async def verify_deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to verify UPI deposit: /verifydep <utr> <amount>"""
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only for administrators.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "**Usage:** `/verifydep <utr> <amount>`\n\n"
            "Example: `/verifydep 123456789012 50.00`",
            parse_mode='Markdown'
        )
        return
    
    try:
        utr = context.args[0]
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0")
            return
        
        admin_id = update.effective_user.id
        user_id = db.verify_deposit(utr, amount, admin_id)
        
        if user_id:
            user = db.get_user(user_id)
            new_balance = user.get('buyer_wallet_balance', 0) if user else 0
            username = user.get('username', 'N/A') if user else 'N/A'
            
            await update.message.reply_text(
                f"✅ **Deposit Verified Successfully!**\n\n"
                f"**UTR:** `{utr}`\n"
                f"**User ID:** {user_id}\n"
                f"**Username:** @{username}\n"
                f"**Amount:** ${amount:.2f}\n"
                f"**New Balance:** ${new_balance:.2f}\n\n"
                f"User has been notified and wallet credited.",
                parse_mode='Markdown'
            )
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"""
✅ **Payment Verified!**

Your deposit has been confirmed and credited to your wallet.

**Amount:** ${amount:.2f}
**New Wallet Balance:** ${new_balance:.2f}
**Transaction ID:** `{utr}`

Thank you for your payment! 🎉
""",
                    parse_mode='Markdown'
                )
                
                await activate_pending_orders(context, user_id)
                
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            await update.message.reply_text(
                f"❌ **Verification Failed**\n\n"
                f"No pending deposit found with UTR: `{utr}`\n\n"
                f"Please check the UTR number and try again.",
                parse_mode='Markdown'
            )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount format. Please use a number (e.g., 50.00)")
    except Exception as e:
        logger.error(f"Error verifying deposit: {e}")
        await update.message.reply_text("❌ An error occurred while verifying the deposit.")

async def view_pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view pending deposits: /deposits"""
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ This command is only for administrators.")
        return
    
    deposits = db.get_pending_deposits()
    
    if not deposits:
        await update.message.reply_text(
            "📋 **No Pending Deposits**\n\n"
            "All deposit requests have been processed."
        )
        return
    
    message = "📋 **Pending Deposit Requests**\n\n"
    
    for deposit in deposits:
        user_id = deposit.get('user_id')
        username = deposit.get('username', 'N/A')
        method = deposit.get('payment_method', 'N/A')
        utr = deposit.get('transaction_id', 'N/A')
        status = deposit.get('status', 'pending')
        created_at = deposit.get('created_at')
        date_text = created_at.strftime('%Y-%m-%d %H:%M') if created_at else 'N/A'
        
        message += f"""
**User:** @{username} (ID: {user_id})
**Method:** {method}
**UTR/TxID:** `{utr}`
**Status:** {status}
**Requested:** {date_text}

"""
    
    message += "\n**To verify:** `/verifydep <utr> <amount>`"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def activate_pending_orders(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Automatically activate pending orders if user has sufficient balance"""
    pending_orders = db.get_pending_orders_for_user(user_id)
    
    if not pending_orders:
        return
    
    user = db.get_user(user_id)
    if not user:
        return
    
    balance = float(user.get('buyer_wallet_balance', 0))
    
    activated_count = 0
    for order in pending_orders:
        order_id = order['id']
        price = float(order['price'])
        
        if balance >= price:
            db.update_user_balance(user_id, -price, 'buyer')
            db.update_order_status(order_id, 'active')
            balance -= price
            activated_count += 1
            
            plan_type = order.get('plan_type', 'Unknown')
            channel = order.get('channel_username', 'N/A')
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"""
🎉 **Plan Activated Automatically!**

**Order ID:** #{order_id}
**Plan:** {plan_type.replace('_', ' ').title()}
**Channel:** {channel}
**Price:** ${price:.2f}
**New Balance:** ${balance:.2f}

Your service is now active and will begin shortly!
""",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id} about order {order_id}: {e}")
    
    if activated_count > 0 and activated_count < len(pending_orders):
        remaining = len(pending_orders) - activated_count
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""
ℹ️ **Insufficient Balance**

You have {remaining} more pending order(s) waiting for activation.

**Current Balance:** ${balance:.2f}

Please add more funds via the Deposit menu to activate remaining orders.
""",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} about remaining orders: {e}")
