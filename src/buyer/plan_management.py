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
from datetime import datetime

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
        plan_type_display = {
            'unlimited_views': '💎 Unlimited Views',
            'limited_views': '🎯 Limited Views',
            'unlimited_reactions': '❤️ Unlimited Reactions',
            'limited_reactions': '🎪 Limited Reactions'
        }.get(order['plan_type'], order['plan_type'])
        
        created_at = order['created_at'].strftime('%Y-%m-%d')
        expires_at = order.get('expires_at')
        expiry_str = expires_at.strftime('%Y-%m-%d') if expires_at else 'Not set'
        
        days_left = 'N/A'
        if expires_at:
            days_left = max(0, (expires_at - datetime.now()).days)
        
        delivered = order.get('delivered_posts', 0)
        total_posts = order.get('total_posts', 0)
        
        message = f"""
📊 **Plan #{order['id']} - {plan_type_display}**

📺 Channel: @{order['channel_username']}
📅 Started: {created_at}
⏳ Expires: {expiry_str} ({days_left} days left)
📈 Progress: {delivered}/{total_posts} posts delivered
⏱️ Delay: {order.get('delay_seconds', 10)} seconds
💰 Price: ${order['price']:.2f}

**Status:** ✅ Active
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 View Details", callback_data=f"plan_view_{order['id']}")],
            [InlineKeyboardButton("⏱️ Change Delay", callback_data=f"plan_delay_{order['id']}")],
            [InlineKeyboardButton("🔄 Renew Plan", callback_data=f"plan_renew_{order['id']}")],
            [InlineKeyboardButton("❌ Cancel Plan", callback_data=f"plan_cancel_{order['id']}")],
        ]
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
    
    plan_type_display = {
        'unlimited_views': '💎 Unlimited Views',
        'limited_views': '🎯 Limited Views',
        'unlimited_reactions': '❤️ Unlimited Reactions',
        'limited_reactions': '🎪 Limited Reactions'
    }.get(order['plan_type'], order['plan_type'])
    
    created_at = order['created_at'].strftime('%Y-%m-%d %H:%M')
    expires_at = order.get('expires_at')
    expiry_str = expires_at.strftime('%Y-%m-%d %H:%M') if expires_at else 'Not set'
    
    message = f"""
📊 **Plan Details #{ order['id']}**

**Plan Type:** {plan_type_display}
**Channel:** @{order['channel_username']}

**Timing:**
• Started: {created_at}
• Expires: {expiry_str}
• Duration: {order['duration']} days

**Delivery Settings:**
• Views/Reactions per post: {order['views_per_post']}
• Total posts (for limited): {order['total_posts']}
• Delivered so far: {order.get('delivered_posts', 0)}
• Delay between actions: {order.get('delay_seconds', 10)} seconds

**Financial:**
• Price: ${order['price']:.2f}
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
    current_delay = order.get('delay_seconds', 10)
    
    await query.edit_message_text(
        f"⏱️ **Change Delay Time**\n\n"
        f"Current delay: **{current_delay} seconds**\n\n"
        f"Enter the new delay time in seconds (5-60):\n"
        f"This controls how many seconds to wait between each view/reaction delivery.",
        parse_mode='Markdown'
    )
    
    return CHANGE_DELAY

async def receive_new_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and update the new delay"""
    try:
        new_delay = int(update.message.text.strip())
        
        if new_delay < 5 or new_delay > 60:
            await update.message.reply_text(
                "❌ Invalid delay time. Please enter a value between 5 and 60 seconds."
            )
            return CHANGE_DELAY
        
        order_id = context.user_data.get('changing_delay_order_id')
        db.update_order_delay(order_id, new_delay)
        
        await update.message.reply_text(
            f"✅ **Delay Updated!**\n\n"
            f"New delay time: **{new_delay} seconds**\n\n"
            f"This will apply to all future deliveries for this plan.",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number between 5 and 60."
        )
        return CHANGE_DELAY

async def renew_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Renew an existing plan"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order_by_id(order_id)
    
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
        plan_type_display = {
            'unlimited_views': '💎 Unlimited Views',
            'limited_views': '🎯 Limited Views',
            'unlimited_reactions': '❤️ Unlimited Reactions',
            'limited_reactions': '🎪 Limited Reactions'
        }.get(order['plan_type'], order['plan_type'])
        
        status_emoji = {'completed': '✅', 'expired': '⏰', 'cancelled': '❌'}.get(order['status'], '📦')
        created_at = order['created_at'].strftime('%Y-%m-%d')
        
        message += f"{status_emoji} **Plan #{order['id']}** - {plan_type_display}\n"
        message += f"  └ @{order['channel_username']} | {created_at} | ${order['price']:.2f}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation"""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

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
