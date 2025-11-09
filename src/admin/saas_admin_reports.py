import logging
import csv
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.database.database import Database
from src.database.config import ADMIN_IDS
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

async def show_saas_reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main SaaS reporting menu"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    keyboard = [
        [InlineKeyboardButton("💳 Payment Reports", callback_data="saas_payments")],
        [InlineKeyboardButton("📊 Sales & Usage Stats", callback_data="saas_sales")],
        [InlineKeyboardButton("📁 Export CSV", callback_data="saas_export")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = """
📊 **SaaS Admin Reports**

Access comprehensive reporting tools:

• **Payment Reports** - View all payments by gateway
• **Sales & Usage Stats** - Today/Week/Month revenue
• **Export CSV** - Download sales or user data

Select an option:
"""
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_payment_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payment reports with gateway filtering"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💳 All Payments", callback_data="payments_all")],
        [InlineKeyboardButton("📱 UPI Payments", callback_data="payments_upi")],
        [InlineKeyboardButton("🎁 Promo Credits", callback_data="payments_promo")],
        [InlineKeyboardButton("📈 Revenue Summary", callback_data="payments_summary")],
        [InlineKeyboardButton("🔙 Back", callback_data="saas_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💳 **Payment Reports**\n\nFilter payments by gateway:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed payment information"""
    query = update.callback_query
    await query.answer()
    
    filter_type = query.data.split('_')[1]
    
    payments = db.get_payment_reports(filter_type)
    
    if not payments:
        await query.edit_message_text(f"No {filter_type} payments found.")
        return
    
    message = f"💳 **{filter_type.upper()} Payment Report**\n\n"
    total = 0
    
    for p in payments[:20]:
        message += f"• #{p['id']} | @{p.get('username', 'N/A')} | ${p['amount']:.2f} | {p['created_at'].strftime('%m/%d')}\n"
        total += float(p['amount'])
    
    message += f"\n**Total:** ${total:.2f}"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="saas_payments")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_revenue_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show revenue summary for Today/Week/Month"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_revenue_summary()
    
    message = f"""
📈 **Revenue Summary**

**Today:**
• Deposits: ${stats['today_deposits']:.2f}
• Sales: ${stats['today_sales']:.2f}
• Orders: {stats['today_orders']}

**This Week:**
• Deposits: ${stats['week_deposits']:.2f}
• Sales: ${stats['week_sales']:.2f}
• Orders: {stats['week_orders']}

**This Month:**
• Deposits: ${stats['month_deposits']:.2f}
• Sales: ${stats['month_sales']:.2f}
• Orders: {stats['month_orders']}

**Lifetime:**
• Total Revenue: ${stats['lifetime_revenue']:.2f}
• Total Orders: {stats['lifetime_orders']}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="saas_payments")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_sales_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sales and service delivery stats"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_sales_stats()
    
    message = f"""
📊 **Sales & Usage Statistics**

**Active Plans:**
• Unlimited Views: {stats['unlimited_views']}
• Limited Views: {stats['limited_views']}
• Unlimited Reactions: {stats['unlimited_reactions']}
• Limited Reactions: {stats['limited_reactions']}

**Service Delivery:**
• Total Posts Delivered: {stats['total_delivered']}
• Pending Deliveries: {stats['pending_deliveries']}
• Active Channels: {stats['active_channels']}

**Account Pool:**
• Active Accounts: {stats['active_accounts']}
• In Use: {stats['accounts_in_use']}
• Available: {stats['available_accounts']}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="saas_reports")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_export_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show CSV export options"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Sales Report", callback_data="export_sales")],
        [InlineKeyboardButton("👥 User Data", callback_data="export_users")],
        [InlineKeyboardButton("📱 Account Pool", callback_data="export_accounts")],
        [InlineKeyboardButton("🔙 Back", callback_data="saas_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📁 **Export Data as CSV**\n\nSelect data to export:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def export_csv_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export data as CSV file"""
    query = update.callback_query
    await query.answer("Generating CSV...")
    
    export_type = query.data.split('_')[1]
    
    data = db.get_export_data(export_type)
    
    if not data:
        await query.edit_message_text("No data available for export.")
        return
    
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    csv_content = output.getvalue()
    output.close()
    
    filename = f"{export_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    await query.message.reply_document(
        document=csv_content.encode('utf-8'),
        filename=filename,
        caption=f"📁 {export_type.title()} Export - {len(data)} records"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="saas_export")]]
    await query.edit_message_text(
        f"✅ Export complete! {len(data)} records exported.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
