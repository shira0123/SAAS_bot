import asyncio
import logging
import schedule
import time
from src.utils.account_status_checker import check_all_accounts, check_pool_and_alert

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_account_check():
    logger.info("Starting scheduled account check...")
    asyncio.run(check_all_accounts())
    asyncio.run(check_pool_and_alert())

schedule.every(6).hours.do(run_account_check)

schedule.every().day.at("02:00").do(run_account_check)

logger.info("Account monitor scheduler started")
logger.info("Account checks will run every 6 hours and daily at 02:00 UTC")
logger.info("Pool alerts will be sent if active accounts drop below 100")
logger.info("Press Ctrl+C to stop")

while True:
    try:
        schedule.run_pending()
        time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        break
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        time.sleep(60)
