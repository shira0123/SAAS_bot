# Telegram Marketplace Bot - Phases 1-7 Complete

## 🚀 Quick Start for AI Agents

### Environment Setup (Replit)
This project runs on Replit with the following configuration:
- **Language**: Python 3.11 (managed via Nix/uv)
- **Database**: PostgreSQL (provisioned via Replit database tools)
- **Package Manager**: uv (pyproject.toml for dependencies)
- **Workflow**: `telegram-bot` runs `python bot.py` in console mode

### Critical Setup Steps (Already Complete ✅)
1. ✅ PostgreSQL database created and connected
2. ✅ All dependencies installed via uv (python-telegram-bot, telethon, psycopg2-binary, etc.)
3. ✅ Database schema initialized (11 tables)
4. ✅ Workflow configured to run bot.py

### Required Secrets (User Must Add)
The bot requires these environment variables to run:
- `BOT_TOKEN` - Telegram Bot API token (from @BotFather)
- `TELEGRAM_API_ID` - Telegram API ID (from my.telegram.org)
- `TELEGRAM_API_HASH` - Telegram API hash (from my.telegram.org)
- `ADMIN_IDS` - Comma-separated list of admin Telegram user IDs

**Status**: ⚠️ Secrets not yet configured by user. Bot will show error until secrets are added.

### How to Work on This Project
1. **Check secrets**: Use `check_secrets` tool to verify required secrets exist
2. **Run the bot**: Workflow auto-restarts on changes, or use `restart_workflow("telegram-bot")`
3. **Check logs**: Use `refresh_all_logs` to see bot console output and errors
4. **Database operations**: Use `database.py` methods or `execute_sql_tool` for queries
5. **Add packages**: Use `packager_tool` with language="python" (updates pyproject.toml automatically)

### File Structure Rules
- **bot.py**: Main entry point, registers all handlers
- **database.py**: All database schema and operations (single source of truth)
- **Feature modules**: Each feature in separate file (account_seller.py, buyer_menu.py, etc.)
- **Never modify**: pyproject.toml manually (use packager_tool instead)

## Project Overview
A sophisticated dual-function Telegram bot that operates as a two-sided marketplace:
- **Seller Side**: Automated purchasing of Telegram accounts from users (✅ Phases 1-4 Complete)
- **Buyer Side**: SaaS platform for delivering automated views and reactions to channel posts (✅ Phases 5-7 Complete)
- **Admin Tools**: Complete account pool management and reporting system (✅ Phase 5 Complete)

## Current Implementation (Phases 1-5)

### Completed Features

#### Phase 1: Foundation (✅ Complete)
1. **Database Schema**: PostgreSQL database with 5 core tables
   - Users: Stores all users (sellers/buyers) with balance tracking
   - Admins: Manages admin users and their roles
   - Sold_Accounts: Stores session strings and account status
   - Withdrawals: Tracks seller payout requests
   - Settings: Stores system configuration (account prices, etc.)

2. **Bot Framework**: 
   - python-telegram-bot for command handling
   - Telethon library for session management
   - Automatic user registration on /start
   - Admin authentication system

3. **Seller Menu**: 5 interactive buttons
   - 💰 Sell TG Account
   - 💸 Withdraw
   - 👤 Profile
   - 🎁 Refer & Earn
   - 💬 Support

#### Phase 2: Account Selling Workflow (✅ Complete)
1. **Conversational Flow**:
   - Phone number collection with regex validation
   - OTP code verification with Telethon
   - 2FA password support for protected accounts
   - Comprehensive error handling and user feedback

2. **Session Management**:
   - Session string creation and secure storage
   - Automatic termination of other active sessions
   - 2FA password reset to default (5000)
   - Session verification before payout

3. **Payment Processing**:
   - Instant payout to seller_balance
   - Automatic referral commission distribution
   - User confirmation before final payout
   - Account status tracking (processing → active)

4. **Admin Controls**:
   - `/setprice` command to adjust account prices
   - Dynamic pricing system stored in settings table
   - Permission-based access control

### Technology Stack
- **Language**: Python 3.11
- **Framework**: python-telegram-bot (v22.5)
- **Session Management**: Telethon (v1.41.2)
- **Database**: PostgreSQL (via psycopg2-binary)
- **Environment**: python-dotenv

### Environment Variables Required
- `BOT_TOKEN`: Telegram Bot API token (from @BotFather)
- `TELEGRAM_API_ID`: Telegram API ID (from my.telegram.org)
- `TELEGRAM_API_HASH`: Telegram API hash (from my.telegram.org)
- `ADMIN_IDS`: Comma-separated list of admin user IDs
- `DATABASE_URL`: PostgreSQL connection string (auto-configured)

### Project Structure
```
.
├── bot.py                       # Main bot logic and handlers
├── account_seller.py            # Account selling conversation flow
├── seller_profile.py            # Seller profile and payout info
├── seller_withdrawals.py        # Withdrawal request handling
├── buyer_menu.py                # Buyer interface and SaaS features
├── admin_controls.py            # Admin withdrawal management
├── admin_reporting.py           # Admin reporting commands
├── account_pool_manager.py      # Account pool management
├── account_status_checker.py    # Automated account status verification
├── account_monitor_scheduler.py # Account monitoring scheduler
├── daily_report.py              # Daily stats report generator
├── run_scheduler.py             # Scheduler for automated reports
├── database.py                  # Database operations and schema
├── config.py                    # Configuration and environment variables
├── setup_admin.py               # Admin setup utility
├── pyproject.toml               # Python dependencies
└── replit.md                   # This file
```

### Phase 4 Features (✅ Complete)
1. **Referral System**:
   - Unique referral links for each user
   - Automatic referral tracking on signup
   - Commission payout on account sales
   - `/setref` admin command to set commission percentage

2. **Admin Reporting**:
   - `/accsell <username>` - View detailed stats for specific user
   - `/alluser [page]` - List all users with pagination
   - `/stats` - Overall system statistics

3. **Support Section**:
   - Support button with helpful information

4. **Daily Automated Reports**:
   - Scheduler sends daily stats to admins at midnight
   - Includes 24-hour and lifetime statistics

### Phase 5 Features (✅ Complete)
1. **Buyer UI (SaaS Interface)**:
   - Complete buyer menu with 7 buttons
   - Buy Plan, Deposit, My Plans interfaces
   - Plan History tracking
   - Buyer Referral Program
   - Reseller Panel system
   - Seamless switching between Seller/Buyer modes

2. **Database Expansion**:
   - `saas_orders` - Store all service orders
   - `saas_rates` - 4 pricing tiers (per view, per day view, per reaction, per day reaction)
   - `promo_codes` - Discount code system
   - `saas_referrals` - Buyer referral tracking
   - `resellers` - Reseller management
   - `account_usage_logs` - Track which account delivers which service

3. **Account Pool Manager**:
   - `/accounts` command to view all accounts
   - Pool statistics (active, banned, full)
   - `/addaccount` - Manually add accounts
   - `/removeaccount <id>` - Remove accounts
   - Pagination support for large pools

4. **Automated Account Monitoring**:
   - `account_status_checker.py` - Checks all account statuses
   - Detects banned/restricted accounts automatically
   - Updates database with current status
   - `account_monitor_scheduler.py` - Runs checks every 6 hours
   - Low pool alert when <100 active accounts
   - Automatic admin notifications

### Phase 6 Features (✅ Phase 6 Complete)

1. **Plan Purchase System (Buy Plan Flow)**:
   - Complete conversation-based order creation flow
   - 4 plan types available:
     - 💎 Unlimited Views - continuous views on posts (pay per day per view)
     - 🎯 Limited Views - one-time view boost (pay per view)
     - ❤️ Unlimited Reactions - auto-reactions on every post (pay per day per reaction)
     - 🎪 Limited Reactions - one-time reaction boost (pay per reaction)
   
2. **Multi-Step Input Collection**:
   - Step 1: Duration (1-365 days)
   - Step 2: Daily posts or daily views/reactions
   - Step 3: Views/reactions per post (for limited plans)
   - Step 4: Channel username/link validation
   - Step 5: Order summary with price calculation
   
3. **Automatic Price Calculation**:
   - Real-time calculation using SaaS rates from database
   - Formula displayed to user for transparency
   - Different formulas for each plan type
   - Examples:
     - Limited Views: days × posts/day × views/post × per_view_rate
     - Unlimited Views: days × views/day × per_day_view_rate
   
4. **Order Creation & Management**:
   - Creates order with `pending_payment` status
   - Stores all plan details in `saas_orders` table
   - Generates unique order ID
   - Links order to user
   - Ready for payment activation (Phase 7)

5. **User Experience Features**:
   - Cancel anytime with `/cancel` command
   - Input validation at each step
   - Clear error messages
   - Progress indicators (Step X/5)
   - Inline keyboard buttons for confirmation

**Files**: `buy_plan.py` (420 lines, complete conversation handler)

### Phase 7 Features (✅ Phase 7 Complete)

1. **Deposit System with Multiple Payment Methods**:
   - 💳 UPI Payment - manual verification with UTR number
   - 💰 Paytm - integration ready (coming soon)
   - ₿ Crypto/CryptoMus - integration ready (coming soon)
   - 🔶 Binance Pay - integration ready (coming soon)
   - 🎁 Apply Promo Code - instant wallet credit
   
2. **UPI Payment Flow**:
   - User sends payment to admin's UPI ID
   - User submits 12-digit UTR number
   - System creates deposit request in database
   - Admin receives notification with UTR details
   - Admin verifies with `/verifydep <utr> <amount>`
   - Wallet automatically credited
   - User notified of successful deposit
   
3. **Promo Code System (Complete)**:
   - **Admin Management** (`/promo` command):
     - Create codes with custom amounts and limits
     - Set expiration dates and usage limits
     - Delete existing codes
     - View all active/inactive codes
     - Track usage logs with timestamps
   
   - **User Experience**:
     - Apply codes from Deposit menu
     - Instant wallet credit upon validation
     - One-time use per user (enforced by database)
     - Clear error messages for invalid/expired/used codes
     - Automatic usage tracking
   
4. **Automated Plan Activation Logic**:
   - Triggers automatically after deposit verification
   - Checks all pending_payment orders for user
   - Verifies wallet balance for each order
   - Activates orders with sufficient balance
   - Deducts payment from wallet
   - Updates order status to "active"
   - Sends activation notifications
   - Handles partial activation (multiple orders)
   - Notifies user if balance insufficient for remaining orders

5. **Database Expansion**:
   - `deposits` table - tracks all deposit requests
   - `promo_code_usage` table - prevents duplicate redemptions
   - New methods: `create_deposit_request()`, `apply_promo_code()`, `verify_deposit()`, `get_pending_deposits()`, `activate_pending_orders()`

6. **Admin Commands**:
   - `/deposits` - View all pending deposit requests
   - `/verifydep <utr> <amount>` - Verify and approve UPI deposits
   - `/promo` - Access promo code management panel

**Files**: 
- `deposit_menu.py` (280 lines) - deposit interface
- `promo_code_management.py` (285 lines) - admin promo management
- `admin_deposit_management.py` (145 lines) - deposit verification & plan activation

### Next Phase: Phase 8 - Service Delivery Engine (🔄 In Progress)

**Objective**: Build the core backend worker that delivers views and reactions to active plans using the account pool.

**Requirements**:

#### 8.1 Core Worker & Channel Joining
- **Delivery Worker**: Separate continuously running script that scans `saas_orders` table for `status: active` plans
- **Channel Join Logic**: 
  - When plan becomes active, get channel link from order
  - Select available accounts from `sold_accounts` pool (status: active, joins < 500)
  - **Public Channels**: Use Telethon/Pyrogram to join channel
  - **Private Channels**: Send join request via accounts
  - Update `joined_channels` count for each account in database
  
#### 8.2 Service Delivery Logic
- **Monitor for New Posts**: Worker monitors all target channels (from active plans)
- **Unlimited Plans**: 
  - On new post → trigger required number of accounts (e.g., 100)
  - Send views/reactions respecting plan's `delay` setting
- **Limited Plans**:
  - On new post → check `daily_posts` quota for that plan
  - If quota not met → deliver views/reactions, increment day's post count
  - If quota met → ignore the post
  - Respect `delay` setting
- **Log Deliveries**: Log all successful deliveries in `account_usage_logs` table

#### 8.3 User-Facing Plan Management
Implement "My Plans" button for buyers with sub-buttons:
- View Current Plan Usage
- Change Delay Time
- Renew Plan
- Cancel Plan

#### 8.4 Plan Expiry & Auto-Leave
- **Plan History**: Implement button to list expired/completed plans
- **Scheduled Job**: Check for expired plans regularly
- **Auto-Leave Logic**: 
  - 3-day grace period after expiry
  - If not renewed → make all associated accounts leave the channel
- **Notifications**: 
  - Send expiry reminders (3 days before, 1 day before, on expiry date)

**Files to Create**:
- `service_delivery_worker.py` - Main delivery engine
- `plan_management.py` - User plan management interface
- `plan_expiry_handler.py` - Expiry checks and auto-leave logic

## User Preferences
- Clean, modular code structure
- Comprehensive database schema
- Interactive menu-based interface
- Secure session and secret management

## Recent Changes
- 2025-11-04: **Project Import to Replit Complete** ✅
  - Successfully migrated project from external environment to Replit
  - Created PostgreSQL database with all environment variables configured
  - Installed all Python dependencies via uv package manager (python-telegram-bot, telethon, psycopg2-binary, python-dotenv, schedule)
  - Resolved package conflicts (removed conflicting "telegram" package that blocked python-telegram-bot)
  - Configured workflow to run `python bot.py` in console mode
  - Verified database connection and schema initialization
  - Bot ready to run once user adds required secrets (BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH, ADMIN_IDS)
  - Added comprehensive AI agent documentation in replit.md for future development
  - Ready for Phase 8 implementation (Service Delivery Engine)
- 2025-11-01: **Phase 7 Implementation Complete** - Automated Payment Integration
  - Implemented complete deposit system with UPI, Paytm, Crypto, Binance options
  - Built promo code management system for admins
  - Created automated plan activation logic
  - Added deposits and promo_code_usage tables to database
  - Implemented admin deposit verification workflow
  - Added user promo code redemption flow
  - Created comprehensive Phase 7 testing guide (21 test cases)
  - Updated all documentation with Phase 7 features
- 2025-11-01: **Phase 6 Documentation Added**
  - Documented complete plan purchase system (Buy Plan flow)
  - Added Phase 6 testing guide for all 4 plan types
  - Updated project structure documentation
- 2025-11-01: **CRITICAL BUG FIX** - Verification Code Issue Resolved
  - **Problem**: Users couldn't receive verification codes when selling accounts
  - **Root Cause**: Telethon client was garbage collected before code entry
  - **Solution**: Persist session string immediately, recreate client for verification
  - **Impact**: Account selling flow now fully functional
  - Added clear UX instructions to check Telegram app for codes
  - Improved error handling and session management
  - Created comprehensive testing guide (TESTING_GUIDE.md)
  - Created feature status report (FEATURE_STATUS.md)
- 2025-10-30: Phase 6 implementation completed
  - Implemented complete plan purchase conversation flow with 5 steps
  - Added 4 plan types (unlimited/limited views/reactions)
  - Built automatic price calculation engine
  - Created order management system with pending_payment status
  - Integrated with existing buyer menu and SaaS database
- 2025-10-30: Phase 5 implementation completed
  - Built complete buyer/SaaS interface with 7 menu options
  - Expanded database with 5 new tables for SaaS operations
  - Implemented account pool manager with manual add/remove
  - Created automated account status checker with Telethon
  - Built low pool alert system (<100 accounts threshold)
  - Added account usage logging mechanism
  - Integrated buyer menu into main bot flow
- 2025-10-30: Phase 4 implementation completed
  - Implemented full referral system with dynamic commission rates
  - Added admin reporting commands (/accsell, /alluser, /stats)
  - Created daily automated report system
  - Added /setref command for admins to control referral percentage
  - Updated Support button with helpful information
- 2025-10-30: Phase 3 implementation completed
  - Seller profile management with payout info
  - Withdrawal request system with admin approval
  - Admin commands for user management (ban, unban, withdrawal control)
  - Withdrawal limits configuration
- 2025-10-30: Phase 2 implementation completed
  - Created complete account selling workflow with Telethon
  - Implemented conversational flow for phone/OTP/2FA collection
  - Added session management (terminate sessions, reset 2FA)
  - Built payout system with referral commission distribution
  - Added admin /setprice command for dynamic pricing
  - Fixed error handling to prevent invalid state transitions
- 2025-10-30: Initial Phase 1 implementation completed
  - Created database schema with 5 core tables (including Settings)
  - Implemented bot framework with user registration
  - Added admin authentication mechanism
  - Built main seller menu with 5 buttons
