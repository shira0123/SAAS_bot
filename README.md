# Telegram Marketplace Bot - Phase 10 Complete ✅

A sophisticated dual-function Telegram bot for a two-sided marketplace where users can sell Telegram accounts and buyers can purchase engagement services. Now with comprehensive SaaS admin reporting, consolidated notifications, broadcast messaging, and admin management!

## ✅ Replit Setup Complete
The bot is now running on Replit with:
- PostgreSQL database configured
- All Python dependencies installed
- OpenSSL system library for Telethon
- Workflow configured to auto-restart bot on changes

## Features Implemented (Phase 1 & 2)

### Database
- **Users Table**: Tracks all users with seller/buyer balances, referral system, and status flags
- **Admins Table**: Manages admin users with roles and permissions
- **Sold_Accounts Table**: Stores account sessions, phone numbers, and usage statistics
- **Withdrawals Table**: Tracks payout requests with approval workflow

### Bot Functionality
- **User Registration**: Automatic registration on /start with referral code support
- **Admin Authentication**: Role-based access control for administrators
- **Seller Menu**: Interactive menu with 5 core features
  - 💰 Sell TG Account - Complete account selling workflow
  - 💸 Withdraw - Request balance withdrawals
  - 👤 Profile - View balance and statistics
  - 🎁 Refer & Earn - Get referral link and earnings
  - 💬 Support - Help and contact information

### Account Selling Workflow (Phase 2)
- **Conversational Flow**: Step-by-step guided process
  - Phone number collection with validation
  - OTP verification with error handling
  - 2FA password support for protected accounts
- **Session Management**: Powered by Telethon
  - Session string creation and storage
  - Automatic termination of other active sessions
  - 2FA password reset to secure default (5000)
- **Verification & Payout**: 
  - User confirmation of logout
  - Session verification before payment
  - Instant payout to seller balance
  - Automatic referral commission distribution
- **Admin Price Control**: 
  - `/setprice` command to adjust account prices
  - Dynamic pricing visible to all users

## How to Use

### For Sellers
1. Start a chat with your bot on Telegram
2. Send `/start` to register and see the main menu
3. Click "💰 Sell TG Account" to begin selling process
4. Follow the step-by-step instructions:
   - Provide your phone number
   - Enter the OTP code sent to your phone
   - If you have 2FA enabled, enter your password
   - Confirm you've been logged out
   - Receive instant payment!
5. Share your referral link to earn commissions on referrals

### For Admins
1. Make sure your Telegram user ID is added to `ADMIN_IDS` in secrets
2. Start the bot with `/start`
3. You'll see an additional admin menu with management options
4. Use `/setprice <amount>` to adjust the account purchase price
   - Example: `/setprice 15.00`
   - View current price: `/setprice`

### Adding an Admin
To add an admin to the database, use the following SQL command:

```sql
INSERT INTO admins (user_id, username, role, is_active)
VALUES (YOUR_TELEGRAM_USER_ID, 'username', 'admin', TRUE);
```

You can execute this through the database tools or add it programmatically.

## Environment Variables

The following secrets are required (already configured in Replit):
- `BOT_TOKEN` - Your Telegram Bot token from @BotFather
- `TELEGRAM_API_ID` - API ID from my.telegram.org
- `TELEGRAM_API_HASH` - API hash from my.telegram.org
- `ADMIN_IDS` - Comma-separated list of admin user IDs
- `DATABASE_URL` - PostgreSQL connection (auto-configured)

## Configuration Options

Edit these values in `config.py` or add them to your environment:
- `ACCOUNT_PRICE` - Payment per account (default: $10.00)
- `MIN_WITHDRAWAL` - Minimum withdrawal amount (default: $5.00)
- `REFERRAL_COMMISSION` - Referral commission rate (default: 10%)

## Testing the Bot

1. The bot is currently running in the console
2. Open Telegram and find your bot
3. Send `/start` to begin
4. Test all menu options to see the interface

## Phase 7 Features (✅ Complete - Automated Payment Integration)

### Deposit System
- **Multiple Payment Methods**:
  - 💳 UPI Payment (Manual verification with UTR)
  - 💰 Paytm (Integration ready)
  - ₿ Crypto/CryptoMus (Integration ready)
  - 🔶 Binance Pay (Integration ready)
  
- **UPI Flow**: Users send payment → Submit UTR → Admin verifies → Wallet credited automatically

### Promo Code System
- **Admin Management**:
  - Create promo codes with custom amounts and limits
  - Set expiration dates and usage limits
  - Delete codes and view usage logs
  - Command: `/promo` for management panel

- **User Experience**:
  - Apply promo codes from Deposit menu
  - Instant wallet credit upon valid code
  - One-time use per user
  - Clear error messages for invalid codes

### Automated Plan Activation
- **Smart Activation**: After deposit verification, system automatically:
  - Checks for pending orders
  - Verifies wallet balance
  - Activates orders and deducts payment
  - Notifies user of activation
  - Shows remaining orders if balance insufficient

### Admin Commands
- `/deposits` - View all pending deposit requests
- `/verifydep <utr> <amount>` - Verify and approve UPI deposits
- `/promo` - Manage promotional codes

## Next Steps (Phase 8+)

The following features are planned for future phases:
- Automated engagement delivery engine
- Service delivery automation (views, reactions)
- Real-time delivery tracking and monitoring
- Reseller approval workflow
- Advanced analytics dashboard

## Project Structure

```
.
├── main.py                         # Entry point
├── src/                            # Source code directory
│   ├── bot/                        # Core bot logic
│   │   ├── bot.py                  # Main bot handlers
│   │   ├── notification_system.py  # Notifications
│   │   ├── daily_report.py         # Daily reports
│   │   └── ...
│   ├── seller/                     # Seller features
│   │   ├── account_seller.py       # Account selling workflow
│   │   ├── seller_profile.py       # Profile management
│   │   └── seller_withdrawals.py   # Withdrawals
│   ├── buyer/                      # Buyer SaaS features
│   │   ├── buyer_menu.py           # Buyer interface
│   │   ├── buy_plan.py             # Plan purchase
│   │   ├── deposit_menu.py         # Deposits
│   │   └── plan_management.py      # Plan management
│   ├── admin/                      # Admin features
│   │   ├── admin_controls.py       # Admin controls
│   │   ├── admin_reporting.py      # Reports
│   │   ├── broadcast_admin.py      # Broadcasting
│   │   └── ...
│   ├── utils/                      # Utilities
│   │   ├── account_pool_manager.py # Account pool
│   │   └── ...
│   └── database/                   # Database
│       ├── database.py             # DB operations
│       └── config.py               # Configuration
├── Dockerfile                      # Docker build config
├── docker-compose.yml              # Docker services
├── fixtodo.md                      # Bug tracker
├── pyproject.toml                  # Python dependencies
├── README.md                       # This file
└── replit.md                       # Project documentation
```

## Database Schema Overview

### Users
- Stores user information, balances, referral data
- Tracks both seller and buyer balances separately
- Includes ban and withdrawal permission flags

### Admins
- Manages administrator accounts
- Supports role-based permissions
- Active/inactive status tracking

### Sold_Accounts
- Stores Telegram session strings
- Tracks account status and usage limits
- Links to seller who provided the account

### Withdrawals
- Records all withdrawal requests
- Tracks processing status and admin approval
- Supports multiple withdrawal methods

## Support

For issues or questions about the bot implementation, refer to the inline code documentation or the project documentation in `replit.md`.

## Phase 9 Features (✅ Complete - Advanced Buyer Features & Reseller Program)

### SaaS Buyer Referral Program
- **Referral System for Buyers**:
  - Earn commission on referred buyer purchases
  - Separate referral balance tracking
  - Custom referral links with tracking
  - Commission rate: 5% (admin configurable)
  
- **Referral Management**:
  - View referral earnings history
  - Track referred users and their purchases
  - Set wallet info for withdrawals
  - Request referral earnings withdrawals

### Buyer Referral Withdrawal System
- **Dedicated Withdrawal Flow**:
  - Separate from seller withdrawals
  - Minimum withdrawal: $5.00
  - Wallet-based payouts (PayPal, Bank, Crypto)
  - Admin approval workflow
  
- **Admin Controls**:
  - View pending buyer referral withdrawals
  - Approve/reject requests with notes
  - Track withdrawal history
  - Automated balance deduction

### Reseller Program
- **Reseller Panel** (User Side):
  - Create custom plan links with margin
  - Set profit margin (5-30%)
  - View sales and commission summary
  - Withdraw commission earnings
  - Track total sales and profits
  
- **Reseller Management** (Admin Side):
  - Approve reseller applications
  - View all resellers and their stats
  - Manage reseller withdrawals
  - Commission summary and top referrers
  - Deactivate/reactivate resellers

### Admin Features
- `/resellermgmt` - Access reseller management panel
- View top buyer referrers
- Set SaaS referral commission rate
- Manage both buyer referral and reseller withdrawals

### Commands for Phase 9
- **For Buyers**: Access via 🎁 Referral Program button
- **For Resellers**: Access via 👔 Reseller Panel button (resellers only)
- **For Admins**: Use `/resellermgmt` command

## Phase 10 Features (✅ Complete - Advanced Admin Tools & Analytics)

### Comprehensive SaaS Admin Reporting
- **Revenue Analytics**:
  - Today/Week/Month revenue summaries
  - New orders tracking and trends
  - Active plan statistics
  - Lifetime revenue metrics
  
- **Payment Gateway Reports**:
  - Filter payments by method (All/UPI/Promo)
  - View detailed payment history
  - Track promo code usage and credits
  - Transaction audit trail
  
- **Sales & Service Delivery Stats**:
  - Active plans by type (Views/Reactions)
  - Posts delivered tracking
  - Account pool usage metrics
  - Active channels monitoring
  
- **CSV Data Export**:
  - Export sales data (1000 records)
  - Export user database
  - Export account pool status
  - Timestamped file generation

### Consolidated Notification System
- **User Notifications**:
  - Payment success confirmations
  - Plan activation alerts
  - Referral commission earned
  - Withdrawal status updates
  - Plan expiry reminders
  
- **Admin Notifications**:
  - New deposit requests
  - New plan purchases
  - Withdrawal requests
  - Referral sales tracking
  - Reseller activity alerts
  - Low account pool warnings

### Broadcast Messaging
- **Targeted Broadcasting**:
  - 👥 All Users - Everyone registered
  - 💎 Active Buyers - Users with active plans
  - ⏰ Expired Buyers - Users with expired plans
  - 👔 Resellers - All active resellers
  
- **Message Types Supported**:
  - Text messages (with Markdown)
  - Photo messages with captions
  - Document messages
  - Success/failure tracking per broadcast

### Admin Management (Root Admin Only)
- **Admin Controls**:
  - ➕ Add new administrators
  - ❌ Remove admin privileges
  - 👥 View all administrators
  - 📜 Admin activity logs
  
- **Admin Activity Tracking**:
  - All admin actions logged
  - Timestamped audit trail
  - User identification
  - Action details recorded

### Enhanced Daily Reports
The automated daily reports now include:
- **SaaS Metrics**: Revenue, new orders, active plans
- **Seller Metrics**: New accounts, withdrawals, registrations
- **Account Pool**: Total, active, banned, full accounts
- **Financial Summary**: All balances and withdrawals
- **Pending Actions**: Withdrawal requests tracking

Sent automatically at midnight UTC to all admins.

### New Admin Commands
- `/saasreports` - Access SaaS reporting dashboard
- `/broadcast` - Send broadcast messages
- `/adminmgmt` - Manage administrators (root only)
- `/resellermgmt` - Manage reseller program

### Database Enhancements
- **New Tables**:
  - `admin_logs` - Track all admin actions
  - `deposit_requests` - Payment tracking
  - `promo_code_usage` - Promo redemption logs
  
- **Enhanced Queries**:
  - Revenue aggregation by time period
  - User segmentation for broadcasts
  - Payment filtering by gateway
  - Export data formatting

