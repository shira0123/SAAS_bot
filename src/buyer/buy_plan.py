import logging
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database
from src.admin.admin_rate_management import get_rate_display_name

logger = logging.getLogger(__name__)

db = Database()

# NEW: Added DRIP_FEED state
(
    PLAN_DAYS,
    PLAN_DAILY_POSTS,
    PLAN_VIEWS_PER_POST,
    PLAN_CHANNEL,
    DRIP_FEED,  # New state for Drip-Feed
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
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def start_plan_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plan type selection and start input collection"""
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
        # --- NEW FLOW for Join & Leave ---
        if 'n_posts' in plan_type:
            # Ask for number of posts
            await query.edit_message_text(
                f"📝 **{plan_name} Plan**\n\n"
                f"This is a one-time service. Accounts will join, service N posts, and then leave.\n\n"
                f"**Step 1/4: How many posts?**\n"
                f"Please enter the number of recent posts you want to service (e.g., 5):\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return JOIN_LEAVE_POST_COUNT
        else:
            # This is a "Recent Post" plan, it only services 1 post.
            context.user_data['post_count'] = 1
            # Skip to asking for Quantity
            await query.edit_message_text(
                f"📝 **{plan_name} Plan**\n\n"
                f"This is a one-time service. Accounts will join, service the single most recent post, and then leave.\n\n"
                f"**Step 1/4: How many {'views' if 'view' in plan_type else 'reactions'}?**\n"
                f"Please enter the total number of {'views' if 'view' in plan_type else 'reactions'} you want delivered (e.g., 500):\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return JOIN_LEAVE_QUANTITY
    else:
        # --- EXISTING FLOW for Standard Plans ---
        await query.edit_message_text(
            f"📝 **{plan_name} Plan**\n\n"
            f"**Step 1/5: Duration**\n\n"
            f"How many days should this service run?\n"
            f"Enter a number between 1 and 365:\n\n"
            f"Or /cancel to go back.",
            parse_mode='Markdown'
        )
        return PLAN_DAYS

async def receive_join_leave_post_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the number of posts for 'Join N Posts' plans"""
    try:
        post_count = int(update.message.text.strip())
        if post_count < 1 or post_count > 50:
            await update.message.reply_text("❌ Please enter a number between 1 and 50:")
            return JOIN_LEAVE_POST_COUNT
        
        context.user_data['post_count'] = post_count
        plan_type = context.user_data['plan_type']
        plan_name = get_rate_display_name(plan_type)

        await update.message.reply_text(
            f"✅ **{plan_name} Plan**\n"
            f"✅ Posts to service: {post_count}\n\n"
            f"**Step 2/4: How many {'views' if 'view' in plan_type else 'reactions'} per post?**\n\n"
            f"Please enter the number of {'views' if 'view' in plan_type else 'reactions'} you want for *each* post (e.g., 100):\n\n"
            f"Or /cancel to go back.",
            parse_mode='Markdown'
        )
        return JOIN_LEAVE_QUANTITY

    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return JOIN_LEAVE_POST_COUNT

async def receive_join_leave_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the quantity of views/reactions for Join/Leave plans"""
    try:
        quantity = int(update.message.text.strip())
        if quantity < 10:
            await update.message.reply_text("❌ Quantity must be at least 10:")
            return JOIN_LEAVE_QUANTITY
        
        context.user_data['quantity_per_post'] = quantity
        plan_type = context.user_data['plan_type']
        plan_name = get_rate_display_name(plan_type)
        
        await update.message.reply_text(
            f"✅ **{plan_name} Plan**\n"
            f"✅ {'Views' if 'view' in plan_type else 'Reactions'} per post: {quantity}\n\n"
            f"**Step 3/4: Channel Link**\n\n"
            f"Please send your channel link or username:\n\n"
            f"Or /cancel to go back.",
            parse_mode='Markdown'
        )
        return JOIN_LEAVE_CHANNEL
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return JOIN_LEAVE_QUANTITY

async def receive_join_leave_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the channel for Join/Leave plans, asks for drip-feed."""
    channel_username = await validate_and_normalize_channel(update)
    if not channel_username:
        return JOIN_LEAVE_CHANNEL
    
    context.user_data['channel_username'] = channel_username
    plan_name = get_rate_display_name(context.user_data['plan_type'])

    await update.message.reply_text(
        f"✅ **{plan_name} Plan**\n"
        f"✅ Channel: {channel_username}\n\n"
        f"**Step 4/4: Drip-Feed (Delay)**\n\n"
        f"How many hours should the delivery be spread over?\n"
        f"Enter a number of hours (e.g., `5` for 5 hours).\n"
        f"Enter `0` for instant delivery.\n\n"
        f"Or /cancel to go back.",
        parse_mode='Markdown'
    )
    return DRIP_FEED


# --- EXISTING FUNCTIONS (Modified) ---

async def validate_and_normalize_channel(update: Update):
    """Helper function to validate channel input."""
    channel = update.message.text.strip()
    
    if re.match(r'^@\w+$', channel):
        channel_username = channel
    elif 't.me/' in channel:
        if 'joinchat/' in channel or 't.me/+' in channel:
             # This is a private invite link
             channel_username = channel # Store the full link
        else:
            # This is a public link
            parts = channel.split('t.me/')
            if len(parts) > 1:
                channel_username = '@' + parts[1].strip('/')
            else:
                await update.message.reply_text("❌ Invalid channel link. Please send a valid link or username.")
                return None
    else:
        channel_username = '@' + channel.lstrip('@')
    
    return channel_username

async def receive_plan_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive number of days (Standard plans only)"""
    try:
        days = int(update.message.text.strip())
        if days < 1 or days > 365:
            await update.message.reply_text("❌ Please enter a number between 1 and 365:")
            return PLAN_DAYS
        
        context.user_data['days'] = days
        plan_type = context.user_data.get('plan_type')
        plan_name = get_rate_display_name(plan_type)
        
        if 'unlimited' in plan_type:
            await update.message.reply_text(
                f"✅ **{plan_name} Plan**\n"
                f"✅ Duration: {days} days\n\n"
                f"**Step 2/4: Daily {'Views' if 'views' in plan_type else 'Reactions'}**\n\n"
                f"How many {'views' if 'views' in plan_type else 'reactions'} per day?\n"
                f"Enter a number:\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_DAILY_POSTS 
        else: # Limited Plans
            await update.message.reply_text(
                f"✅ **{plan_name} Plan**\n"
                f"✅ Duration: {days} days\n\n"
                f"**Step 2/5: Daily Posts**\n\n"
                f"How many posts per day should receive {'views' if 'views' in plan_type else 'reactions'}?\n"
                f"Enter a number:\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_DAILY_POSTS
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return PLAN_DAYS

async def receive_daily_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive daily posts (Limited) or daily views (Unlimited)"""
    try:
        daily_amount = int(update.message.text.strip())
        if daily_amount < 1:
            await update.message.reply_text("❌ Please enter a positive number:")
            return PLAN_DAILY_POSTS
        
        plan_type = context.user_data.get('plan_type')
        plan_name = get_rate_display_name(plan_type)
        
        if 'unlimited' in plan_type:
            context.user_data['daily_views_or_reactions'] = daily_amount
            context.user_data['views_per_post'] = daily_amount
            context.user_data['total_posts'] = 0 # Unlimited
            
            await update.message.reply_text(
                f"✅ **{plan_name} Plan**\n"
                f"✅ Daily {'Views' if 'views' in plan_type else 'Reactions'}: {daily_amount}\n\n"
                f"**Step 3/4: Channel Link**\n\n"
                f"Please send your channel link or username:\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_CHANNEL
        else: # Limited Plans
            context.user_data['daily_posts'] = daily_amount
            
            await update.message.reply_text(
                f"✅ **{plan_name} Plan**\n"
                f"✅ Daily Posts: {daily_amount}\n\n"
                f"**Step 3/5: {'Views' if 'views' in plan_type else 'Reactions'} Per Post**\n\n"
                f"How many {'views' if 'views' in plan_type else 'reactions'} per post?\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_VIEWS_PER_POST
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return PLAN_DAILY_POSTS

async def receive_views_per_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive views/reactions per post (Limited plans only)"""
    try:
        views = int(update.message.text.strip())
        if views < 1:
            await update.message.reply_text("❌ Please enter a positive number:")
            return PLAN_VIEWS_PER_POST
        
        context.user_data['views_per_post'] = views
        plan_type = context.user_data.get('plan_type')
        plan_name = get_rate_display_name(plan_type)
        
        await update.message.reply_text(
            f"✅ **{plan_name} Plan**\n"
            f"✅ {'Views' if 'views' in plan_type else 'Reactions'} Per Post: {views}\n\n"
            f"**Step 4/5: Channel Link**\n\n"
            f"Please send your channel link or username:\n\n"
            f"Or /cancel to go back.",
            parse_mode='Markdown'
        )
        return PLAN_CHANNEL
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number:")
        return PLAN_VIEWS_PER_POST

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive channel link for standard plans, asks for drip-feed."""
    channel_username = await validate_and_normalize_channel(update)
    if not channel_username:
        return PLAN_CHANNEL
    
    context.user_data['channel_username'] = channel_username
    plan_type = context.user_data.get('plan_type')
    plan_name = get_rate_display_name(plan_type)
    
    # Corrected step numbering
    next_step = "5/5" if 'limited' in plan_type else "4/4"
    
    await update.message.reply_text(
        f"✅ **{plan_name} Plan**\n"
        f"✅ Channel: {channel_username}\n\n"
        f"**Step {next_step}: Drip-Feed (Delay)**\n\n"
        f"How many hours should the delivery be spread over **each day**?\n"
        f"Enter a number of hours (e.g., `5` for 5 hours).\n"
        f"Enter `0` for instant delivery.\n\n"
        f"Or /cancel to go back.",
        parse_mode='Markdown'
    )
    return DRIP_FEED

# --- NEW FUNCTION ---
async def receive_drip_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives drip-feed in hours, calculates delay_seconds, and shows summary."""
    try:
        drip_feed_hours = int(update.message.text.strip())
        if drip_feed_hours < 0 or drip_feed_hours > 72:
             await update.message.reply_text("❌ Please enter a number between 0 and 72 hours:")
             return DRIP_FEED
        
        context.user_data['drip_feed_hours'] = drip_feed_hours
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid number (e.g., 5):")
        return DRIP_FEED

    # All flows now merge here to show the final summary
    await show_final_summary(update, context)
    return CONFIRM_ORDER

async def show_final_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculates price and shows the final confirmation for all plan types."""
    ud = context.user_data
    plan_type = ud.get('plan_type')
    plan_name = get_rate_display_name(plan_type)
    channel_username = ud.get('channel_username')
    drip_feed_hours = ud.get('drip_feed_hours', 0)
    
    rates = db.get_saas_rates()
    rate_map = {r['rate_type']: float(r['price_per_unit']) for r in rates}
    rate = rate_map.get(plan_type, 0)
    
    summary = f"📊 **Order Summary**\n\n"
    summary += f"**Plan:** {plan_name}\n"
    summary += f"**Channel:** {channel_username}\n"
    
    total_quantity_per_period = 0 # Used for delay calculation
    
    if 'join' in plan_type:
        # --- Join & Leave Summary ---
        post_count = ud.get('post_count', 1)
        quantity_per_post = ud.get('quantity_per_post', 0)
        total_quantity = post_count * quantity_per_post
        price = total_quantity * rate
        formula = f"{post_count} posts × {quantity_per_post} {'views' if 'view' in plan_type else 'reactions'}/post × ${rate:.4f}"
        
        summary += f"**Posts to Service:** {post_count}\n"
        summary += f"**{'Views' if 'view' in plan_type else 'Reactions'} per Post:** {quantity_per_post}\n"
        
        ud['duration'] = 0 # One-time
        ud['total_posts'] = post_count
        ud['views_per_post'] = quantity_per_post
        ud['daily_posts_limit'] = 0 # Not applicable
        total_quantity_per_period = total_quantity # Drip-feed is for the whole job
        
    elif 'limited' in plan_type:
        # --- Limited (Daily) Summary ---
        days = ud.get('days')
        daily_posts = ud.get('daily_posts')
        views_per_post = ud.get('views_per_post')
        total_quantity = days * daily_posts * views_per_post
        price = total_quantity * rate
        formula = f"{days} days × {daily_posts} posts/day × {views_per_post} {'views' if 'view' in plan_type else 'reactions'}/post × ${rate:.4f}"
        
        summary += f"**Duration:** {days} days\n"
        summary += f"**Daily Posts:** {daily_posts}\n"
        summary += f"**{'Views' if 'view' in plan_type else 'Reactions'} Per Post:** {views_per_post}\n"
        
        ud['total_posts'] = days * daily_posts
        ud['daily_posts_limit'] = daily_posts # NEW
        total_quantity_per_period = daily_posts * views_per_post # Drip-feed is for the *daily* amount
        
    elif 'unlimited' in plan_type:
        # --- Unlimited (Daily) Summary ---
        days = ud.get('days')
        daily_amount = ud.get('daily_views_or_reactions')
        total_quantity = days * daily_amount
        price = total_quantity * rate
        formula = f"{days} days × {daily_amount} {'views' if 'view' in plan_type else 'reactions'}/day × ${rate:.4f}"
        
        summary += f"**Duration:** {days} days\n"
        summary += f"**Daily {'Views' if 'view' in plan_type else 'Reactions'}:** {daily_amount}\n"
        
        ud['total_posts'] = 0 # Unlimited
        ud['views_per_post'] = daily_amount
        ud['daily_posts_limit'] = 0 # Unlimited posts
        total_quantity_per_period = daily_amount # Drip-feed is for the *daily* amount

    # --- Drip-Feed Calculation ---
    delay_seconds = 1 # Default for instant
    if drip_feed_hours > 0:
        total_seconds_per_period = drip_feed_hours * 3600
        
        if total_quantity_per_period > 0:
            delay_seconds = max(1, total_seconds_per_period // total_quantity_per_period)
        
        summary += f"**Drip-Feed:** {drip_feed_hours} hours (Approx. {delay_seconds} sec delay per action)\n"
    else:
        summary += f"**Drip-Feed:** Instant Delivery\n"
        
    ud['delay_seconds'] = delay_seconds
    ud['calculated_price'] = price
    
    summary += f"\n**Calculation:**\n{formula}\n\n"
    summary += f"💰 **Total Price: ${price:.2f}**\n\n"
    summary += "Would you like to proceed to payment?"

    keyboard = [
        [InlineKeyboardButton("✅ Proceed to Payment", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        summary,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create pending order in database for ALL plan types"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    ud = context.user_data
    
    plan_name = get_rate_display_name(ud.get('plan_type'))
    price = ud.get('calculated_price')
    
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
        daily_posts_limit=ud.get('daily_posts_limit', 0) # NEW
    )
    
    await query.edit_message_text(
        f"✅ **Order Created Successfully!**\n\n"
        f"**Order ID:** #{order_id}\n"
        f"**Plan:** {plan_name}\n"
        f"**Amount:** ${price:.2f}\n"
        f"**Status:** Pending Payment\n\n"
        f"💳 **Payment Instructions:**\n"
        f"Please deposit ${price:.2f} to your buyer wallet using the Deposit option.\n\n"
        f"Once payment is confirmed, your order will be activated automatically.\n\n"
        f"Thank you for your order! 🎉",
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel order creation"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ **Order Cancelled**\n\nYou can create a new order anytime.", parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_plan_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel via /cancel command"""
    context.user_data.clear()
    await update.message.reply_text("❌ **Order Cancelled**\n\nYou can create a new order anytime.")
    return ConversationHandler.END

def get_buy_plan_handler():
    """Returns the ConversationHandler for buying plans."""
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