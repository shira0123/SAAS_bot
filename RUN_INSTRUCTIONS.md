````markdown
# 🛠️ Project Runbook: Telegram Bot Service Deployment

This document provides the **chronological steps** required to set up, configure, and launch the Telegram bot project from a clean slate.

## Prerequisites

Ensure the following tools and accounts are ready before beginning:

* **Docker Desktop** installed and running (for containerized environment).
* **Python 3.10+** installed (for local script editing/debugging if necessary).
* A **Telegram account** to obtain API credentials (via [my.telegram.org](https://my.telegram.org/)).
* **Two Telegram Bots** created via `@BotFather` (one for the **Seller/Admin** interface, one for the **Buyer/Client** interface).

***

## Step 1: Environment Configuration

Create the necessary configuration file with your specific credentials.

### 1.1 Create `.env` file

Copy `.env.example` to `.env` or create a new file named `.env` in the project root directory. Fill in the mandatory variables below:

```env
# Telegram API Credentials (from my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here

# Bot Tokens (from @BotFather)
SELLER_BOT_TOKEN=123456:ABC-DefGhIjkLmNoPqRsTuVwXyZ
BUYER_BOT_TOKEN=654321:ZYX-wVTsRqPoNmLkIjHgFeDcBA

# Admin IDs (Comma separated list of Telegram User IDs for system admins)
ADMIN_IDS=1667059792,987654321

# Database Connection (Default settings for Docker deployment)
DATABASE_URL=postgresql://postgres:postgres@telegram_bot_db:5432/saas_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=saas_bot

# Optional: Payment Gateway Keys (Leave blank if not integrating payments yet)
CRYPTOMUS_MERCHANT_ID=
CRYPTOMUS_API_KEY=
````

-----

## Step 2: System Launch

Start the entire microservice ecosystem and the database.

### 2.1 Start the Database and Services

Run this command in the project root directory. This process will build the necessary Docker images and start all containers in detached mode (`-d`).

```bash
docker compose up -d
```

### 2.2 Verify Running Containers

Ensure all services are running correctly. You should see **7 containers** (seller, buyer, delivery, expiry, account, report, and the database) in the output.

```bash
docker compose ps
```

-----

## Step 3: Initial Configuration (Run Once)

Execute these scripts after the initial launch to configure the database.

### 3.1 Grant Admin Privileges

This essential step promotes the User IDs listed in `ADMIN_IDS` within your `.env` file to administrator status in the database.

```bash
docker compose exec seller-bot python -m src.bot.setup_admin
```

### 3.2 Seed Initial Accounts (Optional)

Run this command to import session strings (e.g., from `seed_accounts.py`) into the active account pool for order fulfillment.

```bash
docker compose exec seller-bot python -m seed_accounts
```

-----

## Step 4: Verification & Testing

Confirm the system is operational by monitoring logs and testing the user flow.

### 4.1 Monitor the Delivery Engine

Open a dedicated terminal window and keep this command running. This will show real-time order fulfillment logs.

```bash
docker compose logs -f delivery_worker
```

### 4.2 Test the Buyer Flow

1.  Open your **Buyer Bot** in Telegram.
2.  Run the `/start` command.
3.  **Deposit funds** (Fake a UPI deposit or ask an admin to use the `/promo` command).
4.  **Buy a service** (e.g., a "View N Posts" plan for a test channel).
5.  **Check the logs window** from Step 4.1: You should see messages confirming the delivery process, such as `"Order #1 Starting"`, `"Account Joining"`, etc.

-----

## Step 5: Maintenance Commands

Useful commands for stopping, resetting, or updating the system.

| Action | Command | Notes |
| :--- | :--- | :--- |
| **Stop** the System | `docker compose stop` | Stops all containers gracefully. |
| **Reset** the Database | `docker compose down -v && docker compose up -d` | **DANGEROUS:** Deletes all data, volumes, and restarts the system. |
| **Rebuild** After Code Changes | `docker compose up -d --build` | Rebuilds images from source and restarts containers. |
| **Restart** a Specific Worker | `docker compose restart delivery_worker` | Example for restarting the `delivery_worker` service. |

```

Would you like to run any of the maintenance commands, like stopping the system or checking the logs?
```