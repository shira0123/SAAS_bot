import logging
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database
from src.admin.admin_rate_management import get_rate_display_name

logger = logging.getLogger(__name__)

db = Database()

(
    PLAN_DAYS,
    PLAN_DAILY_POSTS,
    PLAN_VIEWS_PER_POST,
    PLAN_CHANNEL,
    DRIP_FEED,
    CONFIRM_ORDER,
    JOIN_LEAVE_POST_COUNT,
    JOIN_LEAVE_QUANTITY,
    JOIN_LEAVE_CHANNEL,
) = range(9)


async def show_plan_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all 8 plan type options"""
    keyboard = [
        [InlineKeyboardButton("💎 Unlimited Views", callback_data="plan_unlimited_views")],
        [InlineKeyboardButton("🎯 Limited Views", callback_data="plan_limited_views")],
        [InlineKeyboardButton("❤️ Unlimited Reactions", callback_data="plan_unlimited_reactions")],
        [InlineKeyboardButton("🎪 Limited Reactions", callback_data="plan_limited_reactions")],
        [InlineKeyboardButton("🚀 View N Posts & Leave", callback_data="plan_join_view_n_posts")],
        [InlineKeyboardButton("🚀 React to N Posts & Leave", callback_data="plan_join_react_n_posts")],
        [InlineKeyboardButton("⚡ View Recent Post & Leave", callback_data="plan_join_view_recent_post")],
        [InlineKeyboardButton("⚡ React to Recent Post & Leave", callback_data="plan_join_react_recent_post")],
        [InlineKeyboardButton("🔙 Back", callback_data="buyer_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rates = db.get_saas_rates()
    rate_info = ""
    for rate in rates:
        display_name = get_rate_display_name(rate['rate_type'])
        rate_info += f"• {display_name}: ${float(rate['price_per_unit']):.4f}\n"
            
    message = f"""
💎 **Choose Your Service Plan**

**Current Rates:**
{rate_info}

**Plan Types:**

**Standard Plans (Daily Service):**
• **Unlimited Views/Reactions**: Pay per day for continuous service.
• **Limited Views/Reactions**: Pay per post for a set number of days.

**Join & Leave Plans (One-Time Service):**
• **View/React N Posts**: Accounts join, service N posts, then leave.
• **View/React Recent Post**: Accounts join, service 1 post, then leave.

Select a plan to continue:
"""
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def start_plan_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plan_mapping = {
        'plan_unlimited_views': 'unlimited_views',
        'plan_limited_views': 'limited_views',
        'plan_unlimited_reactions': 'unlimited_reactions',
        'plan_limited_reactions': 'limited_reactions',
        'plan_join_view_n_posts': 'join_view_n_posts',
        'plan_join_react_n_posts': 'join_react_n_posts',
        'plan_join_view_recent_post': 'join_view_recent_post',
        'plan_join_react_recent_post': 'join_react_recent_post',
    }
    
    plan_type = plan_mapping.get(query.data)
    context.user_data['plan_type'] = plan_type
    
    plan_name = get_rate_display_name(plan_type)
    
    if 'join' in plan_type:
        if 'n_posts' in plan_type:
            await query.edit_message_text(
                f"📝 **{plan_name} Plan**\n\nThis is a one-time service.\n\n**Step 1/4: How many posts?**\nPlease enter the number of recent posts to service (e.g., 5):\n\nOr /cancel to go back.",
                parse_mode='Markdown'
            )
            return JOIN_LEAVE_POST_COUNT
        else:
            context.user_data['post_count'] = 1
            await query.edit_message_text(
                f"📝 **{plan_name} Plan**\n\nThis is a one-time service.\n\n**Step 1/4: How many {'views' if 'view' in plan_type else 'reactions'}?**\nPlease enter the total number you want delivered (e.g., 500):\n\nOr /cancel to go back.",
                parse_mode='Markdown'
            )
            return JOIN_LEAVE_QUANTITY
    else:
        await query.edit_message_text(
            f"📝 **{plan_name} Plan**\n\n**Step 1/5: Duration**\n\nHow many days should this service run?\nEnter a number (1-365):\n\nOr /cancel to go back.",
            parse_mode='Markdown'
        )
        return PLAN_DAYS

async def receive_join_leave_post_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        post_count = int(update.message.text.strip())
        if post_count < 1 or post_count > 50:
            await update.message.reply_text("❌ Please enter a number between 1 and 50:")
            return JOIN_LEAVE_POST_COUNT
        
        context.user_data['post_count'] = post_count
        plan_type = context.user_data['plan_type']
        
        await update.message.reply_text(
            f"✅ Posts: {post_count}\n\n**Step 2/4: How many {'views' if 'view' in plan_type else 'reactions'} per post?**\n\nOr /cancel to go back.",
            parse_mode='Markdown'
        )
        return JOIN_LEAVE_QUANTITY

    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return JOIN_LEAVE_POST_COUNT

async def receive_join_leave_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        quantity = int(update.message.text.strip())
        if quantity < 10:
            await update.message.reply_text("❌ Quantity must be at least 10:")
            return JOIN_LEAVE_QUANTITY
        
        context.user_data['quantity_per_post'] = quantity
        
        await update.message.reply_text(
            f"✅ Quantity: {quantity}\n\n**Step 3/4: Channel Link**\nPlease send your channel link or username:\n\nOr /cancel to go back.",
            parse_mode='Markdown'
        )
        return JOIN_LEAVE_CHANNEL
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return JOIN_LEAVE_QUANTITY

async def receive_join_leave_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_username = await validate_and_normalize_channel(update)
    if not channel_username:
        return JOIN_LEAVE_CHANNEL
    
    context.user_data['channel_username'] = channel_username
    
    await update.message.reply_text(
        f"✅ Channel: {channel_username}\n\n**Step 4/4: Drip-Feed (Delay)**\n\nHow many hours should the delivery be spread over?\nEnter `0` for instant delivery.\n\nOr /cancel to go back.",
        parse_mode='Markdown'
    )
    return DRIP_FEED

async def validate_and_normalize_channel(update: Update):
    channel = update.message.text.strip()
    if re.match(r'^@\w+$', channel):
        return channel
    elif 't.me/' in channel:
        if 'joinchat/' in channel or 't.me/+' in channel:
             return channel
        else:
            parts = channel.split('t.me/')
            return '@' + parts[1].strip('/') if len(parts) > 1 else None
    else:
        return '@' + channel.lstrip('@')

async def receive_plan_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
        if days < 1 or days > 365:
            await update.message.reply_text("❌ Please enter a number between 1 and 365:")
            return PLAN_DAYS
        
        context.user_data['days'] = days
        plan_type = context.user_data.get('plan_type')
        
        if 'unlimited' in plan_type:
            await update.message.reply_text(
                f"✅ Duration: {days} days\n\n**Step 2/4: Daily {'Views' if 'views' in plan_type else 'Reactions'}**\nHow many per day?\n\nOr /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_DAILY_POSTS 
        else:
            await update.message.reply_text(
                f"✅ Duration: {days} days\n\n**Step 2/5: Daily Posts**\nHow many posts per day to service?\n\nOr /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_DAILY_POSTS
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return PLAN_DAYS

async def receive_daily_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        daily_amount = int(update.message.text.strip())
        if daily_amount < 1:
            await update.message.reply_text("❌ Please enter a positive number:")
            return PLAN_DAILY_POSTS
        
        plan_type = context.user_data.get('plan_type')
        
        if 'unlimited' in plan_type:
            context.user_data['daily_views_or_reactions'] = daily_amount
            context.user_data['views_per_post'] = daily_amount
            context.user_data['total_posts'] = 0
            
            await update.message.reply_text(
                f"✅ Daily Amount: {daily_amount}\n\n**Step 3/4: Channel Link**\nPlease send your channel link:\n\nOr /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_CHANNEL
        else:
            context.user_data['daily_posts'] = daily_amount
            
            await update.message.reply_text(
                f"✅ Daily Posts: {daily_amount}\n\n**Step 3/5: {'Views' if 'views' in plan_type else 'Reactions'} Per Post**\nHow many per post?\n\nOr /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_VIEWS_PER_POST
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return PLAN_DAILY_POSTS

async def receive_views_per_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        views = int(update.message.text.strip())
        if views < 1:
            await update.message.reply_text("❌ Please enter a positive number:")
            return PLAN_VIEWS_PER_POST
        
        context.user_data['views_per_post'] = views
        
        await update.message.reply_text(
            f"✅ Per Post: {views}\n\n**Step 4/5: Channel Link**\nPlease send your channel link:\n\nOr /cancel to go back.",
            parse_mode='Markdown'
        )
        return PLAN_CHANNEL
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return PLAN_VIEWS_PER_POST

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_username = await validate_and_normalize_channel(update)
    if not channel_username:
        return PLAN_CHANNEL
    
    context.user_data['channel_username'] = channel_username
    plan_type = context.user_data.get('plan_type')
    
    next_step = "5/5" if 'limited' in plan_type else "4/4"
    
    await update.message.reply_text(
        f"✅ Channel: {channel_username}\n\n**Step {next_step}: Drip-Feed (Delay)**\n\nHow many hours should the delivery be spread over **each day**?\nEnter `0` for instant.\n\nOr /cancel to go back.",
        parse_mode='Markdown'
    )
    return DRIP_FEED

async def receive_drip_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        drip_feed_hours = int(update.message.text.strip())
        if drip_feed_hours < 0 or drip_feed_hours > 72:
             await update.message.reply_text("❌ Please enter a number between 0 and 72 hours:")
             return DRIP_FEED
        
        context.user_data['drip_feed_hours'] = drip_feed_hours
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number (e.g., 5):")
        return DRIP_FEED

    await show_final_summary(update, context)
    return CONFIRM_ORDER

async def show_final_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    balance = float(user.get('buyer_wallet_balance', 0))
    
    ud = context.user_data
    plan_type = ud.get('plan_type')
    plan_name = get_rate_display_name(plan_type)
    channel_username = ud.get('channel_username')
    drip_feed_hours = ud.get('drip_feed_hours', 0)
    
    rates = db.get_saas_rates()
    rate_map = {r['rate_type']: float(r['price_per_unit']) for r in rates}
    rate = rate_map.get(plan_type, 0)
    
    summary = f"📊 **Order Summary**\n\n**Plan:** {plan_name}\n**Channel:** {channel_username}\n"
    total_quantity_per_period = 0 
    
    if 'join' in plan_type:
        post_count = ud.get('post_count', 1)
        quantity_per_post = ud.get('quantity_per_post', 0)
        total_quantity = post_count * quantity_per_post
        price = total_quantity * rate
        
        summary += f"**Posts:** {post_count}\n**Per Post:** {quantity_per_post}\n"
        
        ud['duration'] = 0
        ud['total_posts'] = post_count
        ud['views_per_post'] = quantity_per_post
        ud['daily_posts_limit'] = 0
        total_quantity_per_period = total_quantity 
        
    elif 'limited' in plan_type:
        days = ud.get('days')
        daily_posts = ud.get('daily_posts')
        views_per_post = ud.get('views_per_post')
        total_quantity = days * daily_posts * views_per_post
        price = total_quantity * rate
        
        summary += f"**Duration:** {days} days\n**Daily Posts:** {daily_posts}\n**Per Post:** {views_per_post}\n"
        
        ud['total_posts'] = days * daily_posts
        ud['daily_posts_limit'] = daily_posts
        total_quantity_per_period = daily_posts * views_per_post
        
    elif 'unlimited' in plan_type:
        days = ud.get('days')
        daily_amount = ud.get('daily_views_or_reactions')
        total_quantity = days * daily_amount
        price = total_quantity * rate
        
        summary += f"**Duration:** {days} days\n**Daily:** {daily_amount}\n"
        
        ud['total_posts'] = 0
        ud['views_per_post'] = daily_amount
        ud['daily_posts_limit'] = 0
        total_quantity_per_period = daily_amount

    delay_seconds = 1 
    if drip_feed_hours > 0:
        total_seconds_per_period = drip_feed_hours * 3600
        if total_quantity_per_period > 0:
            delay_seconds = max(1, total_seconds_per_period // total_quantity_per_period)
        summary += f"**Drip-Feed:** {drip_feed_hours}h (~{delay_seconds}s delay)\n"
    else:
        summary += f"**Drip-Feed:** Instant\n"
        
    ud['delay_seconds'] = delay_seconds
    ud['calculated_price'] = price
    
    summary += f"\n💰 **Total Price: ${price:.2f}**"
    
    # --- NEW: Dynamic Button Logic ---
    if balance >= price:
        summary += f"\n💳 **Wallet Balance:** ${balance:.2f} (✅ Sufficient)\n\nProceed to activate instantly?"
        button_text = "✅ Pay from Wallet & Activate"
    else:
        summary += f"\n💳 **Wallet Balance:** ${balance:.2f} (❌ Insufficient)\n\nYou need ${price - balance:.2f} more."
        button_text = "💳 Proceed to Deposit"

    keyboard = [[InlineKeyboardButton(button_text, callback_data="confirm_order")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    ud = context.user_data
    
    # --- Check Wallet Balance Logic ---
    user = db.get_user(user_id)
    balance = float(user['buyer_wallet_balance'])
    price = float(ud.get('calculated_price'))
    
    plan_name = get_rate_display_name(ud.get('plan_type'))
    
    if balance >= price:
        # 1. Deduct Balance
        db.update_user_balance(user_id, -price, balance_type='buyer')
        
        # 2. Create ACTIVE Order
        order_id = db.create_saas_order(
            user_id=user_id,
            plan_type=ud.get('plan_type'),
            duration=ud.get('duration'),
            views_per_post=ud.get('views_per_post'),
            total_posts=ud.get('total_posts'),
            channel_username=ud.get('channel_username'),
            price=price,
            promo_code=None,
            drip_feed_hours=ud.get('drip_feed_hours', 0),
            delay_seconds=ud.get('delay_seconds', 1),
            daily_posts_limit=ud.get('daily_posts_limit', 0),
            status='active' # ACTIVATED IMMEDIATELY
        )
        
        new_balance = balance - price
        
        await query.edit_message_text(
            f"✅ **Order Activated Successfully!**\n\n"
            f"**Order ID:** #{order_id}\n"
            f"**Plan:** {plan_name}\n"
            f"**Amount Paid:** ${price:.2f}\n"
            f"**Remaining Balance:** ${new_balance:.2f}\n\n"
            f"**Status:** 🚀 Active\n"
            f"The service will start delivering shortly!",
            parse_mode='Markdown'
        )
        
    else:
        # 1. Create PENDING Order
        order_id = db.create_saas_order(
            user_id=user_id,
            plan_type=ud.get('plan_type'),
            duration=ud.get('duration'),
            views_per_post=ud.get('views_per_post'),
            total_posts=ud.get('total_posts'),
            channel_username=ud.get('channel_username'),
            price=price,
            promo_code=None,
            drip_feed_hours=ud.get('drip_feed_hours', 0),
            delay_seconds=ud.get('delay_seconds', 1),
            daily_posts_limit=ud.get('daily_posts_limit', 0),
            status='pending_payment'
        )
        
        await query.edit_message_text(
            f"⚠️ **Insufficient Funds**\n\n"
            f"**Order ID:** #{order_id}\n"
            f"**Plan Cost:** ${price:.2f}\n"
            f"**Your Balance:** ${balance:.2f}\n\n"
            f"**Status:** Pending Payment\n\n"
            f"💳 **Instructions:**\n"
            f"Please deposit at least **${(price - balance):.2f}** to your buyer wallet using the Deposit option.\n\n"
            f"Once you deposit, the order will activate automatically!",
            parse_mode='Markdown'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ **Order Cancelled**", parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_plan_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ **Order Cancelled**")
    return ConversationHandler.END

def get_buy_plan_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_plan_purchase, pattern='^plan_')
        ],
        states={
            # --- Standard Plan States ---
            PLAN_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_plan_days)],
            PLAN_DAILY_POSTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_daily_posts)],
            PLAN_VIEWS_PER_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_views_per_post)],
            PLAN_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)],
            
            # --- Join/Leave Plan States ---
            JOIN_LEAVE_POST_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_join_leave_post_count)],
            JOIN_LEAVE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_join_leave_quantity)],
            JOIN_LEAVE_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_join_leave_channel)],
            
            # --- NEW: Shared Drip-Feed State ---
            DRIP_FEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_drip_feed)],
            
            # --- Shared Final State ---
            CONFIRM_ORDER: [
                CallbackQueryHandler(confirm_order, pattern='^confirm_order$'),
                CallbackQueryHandler(cancel_order, pattern='^cancel_order$')
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_plan_purchase)
        ],
        name="buy_plan",
        persistent=False
    )