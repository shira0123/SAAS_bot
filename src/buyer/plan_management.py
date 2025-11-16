import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from src.database.database import Database
from datetime import datetime, date

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

CHANGE_DELAY, RENEW_PLAN = range(2)

async def show_my_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's active plans"""
    user_id = update.effective_user.id
    
    active_orders = db.get_user_active_orders(user_id)
    
    if not active_orders:
        await update.message.reply_text(
            "📋 **My Active Plans**\n\n"
            "You don't have any active plans at the moment.\n\n"
            "Use the 💎 Buy Plan button to purchase a new plan!",
            parse_mode='Markdown'
        )
        return
    
    for order in active_orders:
        from src.admin.admin_rate_management import get_rate_display_name
        plan_type_display = get_rate_display_name(order['plan_type'])
        
        created_at = order['created_at'].strftime('%Y-%m-%d')
        
        # Handle different plan types
        if order['duration'] > 0:
            # Standard Daily Plan
            expires_at = order.get('expires_at')
            expiry_str = expires_at.strftime('%Y-%m-%d') if expires_at else 'Not set'
            days_left = 'N/A'
            if expires_at:
                days_left = max(0, (expires_at - datetime.now()).days)
            
            if order['plan_type'].startswith('limited'):
                # NEW: Daily Quota Display
                daily_limit = order.get('daily_posts_limit', 0)
                daily_count = order.get('daily_delivery_count', 0)
                last_date = order.get('last_delivery_date')
                if last_date != date.today(): # Reset if it's a new day
                    daily_count = 0
                progress = f"Today: {daily_count}/{daily_limit} posts | Total: {order.get('delivered_posts', 0)}/{order['total_posts']} posts"
            else:
                # Unlimited Plan
                progress = f"{order.get('delivered_posts', 0)} posts delivered"
                
            timing = f"⏳ Expires: {expiry_str} ({days_left} days left)"
            
        else:
            # One-Time Join & Leave Plan
            progress = f"{order.get('delivered_posts', 0)}/{order['total_posts']} posts"
            timing = "⏱️ One-Time Job"

        
        drip_feed_hours = order.get('drip_feed_hours', 0)
        delay_str = f"{drip_feed_hours} hours" if drip_feed_hours > 0 else "Instant"

        message = f"""
📊 **Plan #{order['id']} - {plan_type_display}**

📺 Channel: @{order['channel_username']}
📅 Started: {created_at}
{timing}
📈 Progress: {progress}
⏱️ Drip-Feed: {delay_str}
💰 Price: ${float(order['price']):.2f}

**Status:** ✅ Active
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 View Details", callback_data=f"plan_view_{order['id']}")],
            [InlineKeyboardButton("⏱️ Change Drip-Feed", callback_data=f"plan_delay_{order['id']}")],
            # [InlineKeyboardButton("🔄 Renew Plan", callback_data=f"plan_renew_{order['id']}")], # TODO
            [InlineKeyboardButton("❌ Cancel Plan", callback_data=f"plan_cancel_{order['id']}")],
        ]
        
        # Cannot change delay on one-time jobs
        if order['duration'] == 0:
            keyboard.pop(1) 
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def view_plan_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View detailed plan information"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order_by_id(order_id)
    
    if not order:
        await query.edit_message_text("❌ Plan not found.")
        return
    
    user_id = query.from_user.id
    if order['user_id'] != user_id:
        await query.edit_message_text("❌ This plan doesn't belong to you.")
        return
    
    from src.admin.admin_rate_management import get_rate_display_name
    plan_type_display = get_rate_display_name(order['plan_type'])
    
    created_at = order['created_at'].strftime('%Y-%m-%d %H:%M')
    
    message = f"""
📊 **Plan Details #{ order['id']}**

**Plan Type:** {plan_type_display}
**Channel:** @{order['channel_username']}
"""

    if order['duration'] > 0:
        # Standard Daily Plan
        expires_at = order.get('expires_at')
        expiry_str = expires_at.strftime('%Y-%m-%d %H:%M') if expires_at else 'Not set'
        message += f"""
**Timing:**
• Started: {created_at}
• Expires: {expiry_str}
• Duration: {order['duration']} days
"""
        if order['plan_type'].startswith('limited'):
             message += f"""
**Delivery Settings:**
• Posts per day: {order['daily_posts_limit']}
• Views/Reactions per post: {order['views_per_post']}
• Total posts in plan: {order['total_posts']}
• Total delivered so far: {order.get('delivered_posts', 0)}
"""
        else: # Unlimited
            message += f"""
**Delivery Settings:**
• Views/Reactions per day: {order['views_per_post']}
• Posts per day: Unlimited
• Total delivered so far: {order.get('delivered_posts', 0)}
"""
    else:
        # One-Time Join & Leave Plan
        message += f"""
**Timing:**
• Created: {created_at}
• Type: One-Time Job
"""
        message += f"""
**Delivery Settings:**
• Total Posts to Service: {order['total_posts']}
• Views/Reactions per post: {order['views_per_post']}
• Delivered so far: {order.get('delivered_posts', 0)}
"""

    drip_feed_hours = order.get('drip_feed_hours', 0)
    delay_str = f"{drip_feed_hours} hours" if drip_feed_hours > 0 else "Instant"

    message += f"• Drip-Feed: {delay_str} (Approx. {order.get('delay_seconds', 1)}s delay)\n"

    message += f"""
**Financial:**
• Price: ${float(order['price']):.2f}
{f"• Promo code used: {order.get('promo_code')}" if order.get('promo_code') else ''}

**Status:** ✅ {order['status'].title()}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Plans", callback_data="plans_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def start_change_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start delay change process"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    context.user_data['changing_delay_order_id'] = order_id
    
    order = db.get_order_by_id(order_id)
    
    if order['duration'] == 0:
        await query.edit_message_text("❌ You cannot change the delay on a one-time 'Join & Leave' plan after it has started.")
        return ConversationHandler.END
        
    current_delay = order.get('drip_feed_hours', 0)
    
    await query.edit_message_text(
        f"⏱️ **Change Drip-Feed Time**\n\n"
        f"Current drip-feed: **{current_delay} hours** (per day)\n\n"
        f"Enter the new duration in hours (0-72):\n"
        f"(0 = Instant, 5 = 5 hours)\n\n"
        f"This controls how long the *daily* service is spread out over.",
        parse_mode='Markdown'
    )
    
    return CHANGE_DELAY

async def receive_new_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and update the new delay"""
    try:
        new_drip_feed_hours = int(update.message.text.strip())
        
        if new_drip_feed_hours < 0 or new_drip_feed_hours > 72:
            await update.message.reply_text(
                "❌ Invalid duration. Please enter a value between 0 and 72 hours."
            )
            return CHANGE_DELAY
        
        order_id = context.user_data.get('changing_delay_order_id')
        order = db.get_order_by_id(order_id)
        
        # --- Recalculate delay_seconds ---
        delay_seconds = 1
        if new_drip_feed_hours > 0:
            total_seconds = new_drip_feed_hours * 3600
            
            # For daily plans, quantity is views_per_post (for unlimited)
            # or views_per_post * daily_posts_limit (for limited)
            if order['plan_type'].startswith('limited'):
                quantity_per_period = order['views_per_post'] * order['daily_posts_limit']
            else: # Unlimited
                quantity_per_period = order['views_per_post']

            if quantity_per_period > 0:
                delay_seconds = max(1, total_seconds // quantity_per_period)
        
        db.update_order_delay(order_id, delay_seconds, new_drip_feed_hours)
        
        await update.message.reply_text(
            f"✅ **Drip-Feed Updated!**\n\n"
            f"New duration: **{new_drip_feed_hours} hours**\n"
            f"New calculated delay: ~{delay_seconds} sec/action\n\n"
            f"This will apply to all future deliveries for this plan.",
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number between 0 and 72."
        )
        return CHANGE_DELAY

async def renew_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Renew an existing plan (Placeholder)"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    
    await query.edit_message_text(
        f"🔄 **Renew Plan**\n\n"
        f"Plan #{order_id} renewal feature will be implemented soon!\n\n"
        f"For now, please create a new plan using the 💎 Buy Plan button.",
        parse_mode='Markdown'
    )

async def cancel_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel an existing plan"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order_by_id(order_id)
    
    if not order:
        await query.edit_message_text("❌ Plan not found.")
        return
        
    user_id = query.from_user.id
    if order['user_id'] != user_id:
        await query.edit_message_text("❌ This plan doesn't belong to you.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Cancel", callback_data=f"confirm_cancel_{order_id}"),
            InlineKeyboardButton("❌ No, Keep It", callback_data="plans_back")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ **Cancel Plan?**\n\n"
        f"Are you sure you want to cancel Plan #{order_id}?\n\n"
        f"This action cannot be undone. The plan will stop immediately.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def confirm_cancel_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm plan cancellation"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    
    db.update_order_status(order_id, 'cancelled')
    
    await query.edit_message_text(
        f"✅ **Plan Cancelled**\n\n"
        f"Plan #{order_id} has been cancelled successfully.\n\n"
        f"You can view your cancelled plans in the Plan History.",
        parse_mode='Markdown'
    )

async def show_plan_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's plan history (expired/completed/cancelled)"""
    user_id = update.effective_user.id
    
    history_orders = db.get_user_order_history(user_id, limit=20)
    
    if not history_orders:
        await update.message.reply_text(
            "📋 **Plan History**\n\n"
            "You don't have any completed or cancelled plans yet.",
            parse_mode='Markdown'
        )
        return
    
    message = "📋 **Plan History**\n\n"
    
    for order in history_orders:
        from src.admin.admin_rate_management import get_rate_display_name
        plan_type_display = get_rate_display_name(order['plan_type'])
        
        status_emoji = {'completed': '✅', 'expired': '⏰', 'cancelled': '❌', 'failed': '❗️'}.get(order['status'], '📦')
        created_at = order['created_at'].strftime('%Y-%m-%d')
        
        message += f"{status_emoji} **Plan #{order['id']}** - {plan_type_display}\n"
        message += f"  └ @{order['channel_username']} | {created_at} | ${float(order['price']):.2f}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation"""
    await update.message.reply_text("Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

async def back_to_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for 'Back to Plans' button"""
    query = update.callback_query
    await query.answer()
    # This is a bit of a hack; we just re-send the main "My Plans" message
    # We need to send it as a new message, so we reply to the original user
    await query.message.delete()
    # Find the original message that triggered the "My Plans" button
    original_message = update.callback_query.message.reply_to_message
    if not original_message:
        # Fallback if the original message can't be found
        original_message = update.callback_query.message
    await show_my_plans(original_message, context)


def get_plan_management_handler():
    """Get the conversation handler for plan management"""
    delay_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_change_delay, pattern="^plan_delay_")],
        states={
            CHANGE_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_delay)],
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
    )
    
    return delay_handler