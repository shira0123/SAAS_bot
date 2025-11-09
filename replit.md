# Telegram Marketplace Bot

## Overview
This project is a sophisticated dual-function Telegram bot designed to operate as a two-sided marketplace. It facilitates the automated purchasing of Telegram accounts from sellers and provides a SaaS platform for buyers to deliver automated views and reactions to Telegram channel posts. The bot includes comprehensive admin tools for account pool management, reporting, and payment processing.

**Key Capabilities:**
- **Seller Side**: Automated workflow for users to sell Telegram accounts, including phone number/OTP/2FA verification, secure session storage, and instant payouts with referral commissions.
- **Buyer Side**: A SaaS platform offering various plans for automated views and reactions, deposit systems with multiple payment methods (UPI, crypto, etc.), promo code functionality, and plan management.
- **Admin Tools**: Extensive features for managing user accounts, account pools, pricing, referral commissions, deposits, and automated reporting.
- **Automated Account Monitoring**: System to check account statuses, detect banned accounts, and manage the active account pool.

## User Preferences
- Clean, modular code structure
- Comprehensive database schema
- Interactive menu-based interface
- Secure session and secret management
- Always Update TESTING_GUIDE.md: When implementing any new phase or major feature:
   - Add comprehensive test cases to TESTING_GUIDE.md
   - Include step-by-step testing instructions
   - Add a verification checklist for the phase
   - Update the "Working Features" section to reflect new functionality
   - Update the "Not Yet Implemented" section to remove completed features

## System Architecture
The bot is built on Python 3.11, utilizing `python-telegram-bot` for handling Telegram interactions and `Telethon` for direct Telegram API operations like session management and account verification. PostgreSQL is used as the primary database, managed via `psycopg2-binary`. The project follows a modular structure with dedicated directories for bot logic, database operations, admin features, seller workflows, buyer functionalities, and shared utilities.

**UI/UX Decisions:**
- Interactive menu-based interface with inline keyboard buttons for conversational flows.
- Clear user feedback, error handling, and progress indicators in multi-step processes.
- Seamless switching between Seller and Buyer modes.

**Technical Implementations:**
- **Conversational Flows**: Extensively uses `python-telegram-bot`'s conversation handlers for multi-step user interactions (e.g., account selling, plan purchasing).
- **Session Management**: Leverages `Telethon` for creating, storing, and managing Telegram user sessions securely, including handling OTP and 2FA verification.
- **Dynamic Pricing & Rates**: All pricing (account sales, SaaS plans) is dynamically fetched from the database, allowing admin configuration.
- **Automated Tasks**: Scheduled jobs for daily reports, account status checks, and future service delivery.
- **Database Schema**: Designed with 11 core tables including `users`, `sold_accounts`, `saas_orders`, `saas_rates`, `deposits`, and `promo_codes` to support marketplace and SaaS functionalities.

**Feature Specifications:**
- **Account Selling Workflow**: Guides sellers through providing phone number, OTP, and 2FA password, then stores session and pays out.
- **Buyer SaaS Platform**: Offers unlimited/limited views and reactions plans, with a multi-step purchase conversation, real-time price calculation, and order management.
- **Payment Systems**: Supports UPI for deposits with manual admin verification, and integrates a promo code system for discounts.
- **Account Pool Management**: Admin commands to view, add, remove accounts, and monitor pool statistics.
- **Referral System**: Tracks referrals and automates commission payouts for both sellers and buyers.
- **Admin Reporting**: Commands for user statistics, account sales, and overall system metrics.

## External Dependencies
- **Telegram Bot API**: Primary interface for bot communication (via `python-telegram-bot`).
- **Telegram API (MTProto)**: Used for direct interaction with Telegram accounts (via `Telethon`) for session management, verification, and service delivery.
- **PostgreSQL**: Relational database for all persistent data storage.
- **Nix/uv**: Package management and environment setup.
- **python-dotenv**: For managing environment variables.