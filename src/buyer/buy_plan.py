import logging
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from src.database.database import Database

logger = logging.getLogger(__name__)

db = Database()

PLAN_DAYS, PLAN_DAILY_POSTS, PLAN_VIEWS_PER_POST, PLAN_DELAY, PLAN_CHANNEL, CONFIRM_ORDER = range(6)

async def show_plan_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the 4 plan type options"""
    keyboard = [
        [InlineKeyboardButton("💎 Unlimited Views", callback_data="plan_unlimited_views")],
        [InlineKeyboardButton("🎯 Limited Views", callback_data="plan_limited_views")],
        [InlineKeyboardButton("❤️ Unlimited Reactions", callback_data="plan_unlimited_reactions")],
        [InlineKeyboardButton("🎪 Limited Reactions", callback_data="plan_limited_reactions")],
        [InlineKeyboardButton("🔙 Back", callback_data="buyer_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rates = db.get_saas_rates()
    rate_info = ""
    for rate in rates:
        rate_info += f"• {rate['rate_type'].replace('_', ' ').title()}: ${rate['price_per_unit']:.4f}\n"
    
    message = f"""
💎 **Choose Your Service Plan**

**Current Rates:**
{rate_info}

**Plan Types:**

**Unlimited Views**: Get continuous views on your posts
• Pay per day per view
• Best for consistent growth

**Limited Views**: One-time view boost
• Pay per view
• Perfect for single posts

**Unlimited Reactions**: Auto-reactions on every post
• Pay per day per reaction
• Ongoing engagement

**Limited Reactions**: One-time reaction boost
• Pay per reaction
• Quick engagement spike

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
        'plan_limited_reactions': 'limited_reactions'
    }
    
    plan_type = plan_mapping.get(query.data)
    context.user_data['plan_type'] = plan_type
    
    plan_names = {
        'unlimited_views': '💎 Unlimited Views',
        'limited_views': '🎯 Limited Views',
        'unlimited_reactions': '❤️ Unlimited Reactions',
        'limited_reactions': '🎪 Limited Reactions'
    }
    
    plan_name = plan_names.get(plan_type)
    
    await query.edit_message_text(
        f"📝 **{plan_name} Plan**\n\n"
        f"Step 1/5: Duration\n\n"
        f"How many days should this service run?\n"
        f"Enter a number between 1 and 365:\n\n"
        f"Or /cancel to go back.",
        parse_mode='Markdown'
    )
    
    return PLAN_DAYS

async def receive_plan_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive number of days"""
    try:
        days = int(update.message.text.strip())
        
        if days < 1 or days > 365:
            await update.message.reply_text(
                "❌ Please enter a number between 1 and 365:"
            )
            return PLAN_DAYS
        
        context.user_data['days'] = days
        
        plan_type = context.user_data.get('plan_type')
        
        if 'unlimited' in plan_type:
            await update.message.reply_text(
                f"✅ Duration: {days} days\n\n"
                f"Step 2/5: Daily Posts/Views\n\n"
                f"How many {'views' if 'views' in plan_type else 'reactions'} per day?\n"
                f"Enter a number:\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"✅ Duration: {days} days\n\n"
                f"Step 2/5: Daily Posts\n\n"
                f"How many posts per day should receive {'views' if 'views' in plan_type else 'reactions'}?\n"
                f"Enter a number:\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
        
        return PLAN_DAILY_POSTS
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number. Please enter a valid number:"
        )
        return PLAN_DAYS

async def receive_daily_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive daily posts or daily views"""
    try:
        daily = int(update.message.text.strip())
        
        if daily < 1:
            await update.message.reply_text(
                "❌ Please enter a positive number:"
            )
            return PLAN_DAILY_POSTS
        
        plan_type = context.user_data.get('plan_type')
        
        if 'unlimited' in plan_type:
            context.user_data['daily_views'] = daily
            context.user_data['views_per_post'] = daily
            context.user_data['total_posts'] = context.user_data['days'] * 1
            
            await update.message.reply_text(
                f"✅ Daily {'Views' if 'views' in plan_type else 'Reactions'}: {daily}\n\n"
                f"Step 3/5: Channel Link\n\n"
                f"Please send your channel link or username:\n"
                f"Example: @yourchannel or https://t.me/yourchannel\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_CHANNEL
        else:
            context.user_data['daily_posts'] = daily
            context.user_data['total_posts'] = context.user_data['days'] * daily
            
            await update.message.reply_text(
                f"✅ Daily Posts: {daily}\n\n"
                f"Step 3/5: {'Views' if 'views' in plan_type else 'Reactions'} Per Post\n\n"
                f"How many {'views' if 'views' in plan_type else 'reactions'} per post?\n"
                f"Enter a number:\n\n"
                f"Or /cancel to go back.",
                parse_mode='Markdown'
            )
            return PLAN_VIEWS_PER_POST
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number. Please enter a valid number:"
        )
        return PLAN_DAILY_POSTS

async def receive_views_per_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive views/reactions per post (Limited plans only)"""
    try:
        views = int(update.message.text.strip())
        
        if views < 1:
            await update.message.reply_text(
                "❌ Please enter a positive number:"
            )
            return PLAN_VIEWS_PER_POST
        
        context.user_data['views_per_post'] = views
        
        plan_type = context.user_data.get('plan_type')
        
        await update.message.reply_text(
            f"✅ {'Views' if 'views' in plan_type else 'Reactions'} Per Post: {views}\n\n"
            f"Step 4/5: Channel Link\n\n"
            f"Please send your channel link or username:\n"
            f"Example: @yourchannel or https://t.me/yourchannel\n\n"
            f"Or /cancel to go back.",
            parse_mode='Markdown'
        )
        
        return PLAN_CHANNEL
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number. Please enter a valid number:"
        )
        return PLAN_VIEWS_PER_POST

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive channel link and calculate price"""
    channel = update.message.text.strip()
    
    if re.match(r'^@\w+$', channel):
        channel_username = channel
    elif 't.me/' in channel:
        parts = channel.split('t.me/')
        if len(parts) > 1:
            channel_username = '@' + parts[1].strip('/')
        else:
            await update.message.reply_text(
                "❌ Invalid channel link. Please send a valid link:\n"
                "Example: @yourchannel or https://t.me/yourchannel"
            )
            return PLAN_CHANNEL
    else:
        channel_username = '@' + channel.lstrip('@')
    
    context.user_data['channel_username'] = channel_username
    
    plan_type = context.user_data.get('plan_type')
    days = context.user_data.get('days')
    views_per_post = context.user_data.get('views_per_post')
    total_posts = context.user_data.get('total_posts')
    daily_posts = context.user_data.get('daily_posts', 0)
    daily_views = context.user_data.get('daily_views', 0)
    
    rates = db.get_saas_rates()
    rate_map = {r['rate_type']: r['price_per_unit'] for r in rates}
    
    if plan_type == 'limited_views':
        price = days * daily_posts * views_per_post * rate_map.get('per_view', 0.001)
        formula = f"{days} days × {daily_posts} posts/day × {views_per_post} views/post × ${rate_map.get('per_view', 0.001):.4f}"
    elif plan_type == 'unlimited_views':
        price = days * daily_views * rate_map.get('per_day_view', 0.05)
        formula = f"{days} days × {daily_views} views/day × ${rate_map.get('per_day_view', 0.05):.4f}"
    elif plan_type == 'limited_reactions':
        price = days * daily_posts * views_per_post * rate_map.get('per_reaction', 0.002)
        formula = f"{days} days × {daily_posts} posts/day × {views_per_post} reactions/post × ${rate_map.get('per_reaction', 0.002):.4f}"
    elif plan_type == 'unlimited_reactions':
        price = days * daily_views * rate_map.get('per_day_reaction', 0.08)
        formula = f"{days} days × {daily_views} reactions/day × ${rate_map.get('per_day_reaction', 0.08):.4f}"
    else:
        price = 0
        formula = "Unknown plan"
    
    context.user_data['calculated_price'] = price
    
    plan_names = {
        'unlimited_views': '💎 Unlimited Views',
        'limited_views': '🎯 Limited Views',
        'unlimited_reactions': '❤️ Unlimited Reactions',
        'limited_reactions': '🎪 Limited Reactions'
    }
    
    summary = f"""
📊 **Order Summary**

**Plan:** {plan_names.get(plan_type)}
**Channel:** {channel_username}
**Duration:** {days} days
"""
    
    if 'unlimited' in plan_type:
        summary += f"**Daily {'Views' if 'views' in plan_type else 'Reactions'}:** {daily_views}\n"
    else:
        summary += f"**Daily Posts:** {daily_posts}\n"
        summary += f"**{'Views' if 'views' in plan_type else 'Reactions'} Per Post:** {views_per_post}\n"
    
    summary += f"""
**Calculation:**
{formula}

💰 **Total Price: ${price:.2f}**

Would you like to proceed to payment?
"""
    
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
    
    return CONFIRM_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create pending order"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    plan_type = context.user_data.get('plan_type')
    days = context.user_data.get('days')
    views_per_post = context.user_data.get('views_per_post')
    total_posts = context.user_data.get('total_posts')
    channel_username = context.user_data.get('channel_username')
    price = context.user_data.get('calculated_price')
    
    order_id = db.create_saas_order(
        user_id=user_id,
        plan_type=plan_type,
        duration=days,
        views_per_post=views_per_post,
        total_posts=total_posts,
        channel_username=channel_username,
        price=price,
        promo_code=None
    )
    
    plan_names = {
        'unlimited_views': '💎 Unlimited Views',
        'limited_views': '🎯 Limited Views',
        'unlimited_reactions': '❤️ Unlimited Reactions',
        'limited_reactions': '🎪 Limited Reactions'
    }
    
    await query.edit_message_text(
        f"✅ **Order Created Successfully!**\n\n"
        f"**Order ID:** #{order_id}\n"
        f"**Plan:** {plan_names.get(plan_type)}\n"
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
    
    await query.edit_message_text(
        "❌ **Order Cancelled**\n\n"
        "You can create a new order anytime from the Buy Plan menu.",
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_plan_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel via /cancel command"""
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ **Order Cancelled**\n\n"
        "You can create a new order anytime from the Buy Plan menu."
    )
    
    return ConversationHandler.END

def get_buy_plan_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_plan_purchase, pattern='^plan_(unlimited_views|limited_views|unlimited_reactions|limited_reactions)$')
        ],
        states={
            PLAN_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_plan_days)
            ],
            PLAN_DAILY_POSTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_daily_posts)
            ],
            PLAN_VIEWS_PER_POST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_views_per_post)
            ],
            PLAN_CHANNEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)
            ],
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
