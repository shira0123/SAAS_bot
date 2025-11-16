# Refactor: Implement Two-Bot Architecture

[cite_start]This commit performs the major architectural refactor from a single-bot system to the two-bot ecosystem (Seller Bot and Buyer Bot) as originally defined in the project plan[cite: 50, 60, 119].

This separation is a critical step for scalability and clean separation of concerns.

## Core Changes

* **New Bot Entrypoints:**
    * Created `main_seller.py` to run Bot 1 (The Acquisition Bot).
    * Created `main_buyer.py` to run Bot 2 (The Service Bot).

* **Docker Orchestration:**
    * Updated `docker-compose.yml` to run **6 services**:
        1.  `seller-bot` (runs `main_seller.py`)
        2.  `buyer-bot` (runs `main_buyer.py`)
        3.  `report_worker`
        4.  `account_worker`
        5.  `delivery_worker`
        6.  `expiry_worker`

* **Configuration Update:**
    * Modified `src/database/config.py` to replace the single `BOT_TOKEN` with `SELLER_BOT_TOKEN` and `BUYER_BOT_TOKEN`.
    * Updated worker scripts (`daily_report.py`, `account_status_checker.py`, `plan_expiry_handler.py`) to use the new `BUYER_BOT_TOKEN` for sending notifications.

* **Code Cleanup:**
    * Deleted the obsolete `main.py` and `src/bot/bot.py` files.
    * Removed the "Back to Seller Menu" button from `src/buyer/buyer_menu.py` to enforce separation.

* **Bug Fix:**
    * Added a `healthcheck` to the `postgres` service in `docker-compose.yml` to prevent the bot services from crash-looping on startup.