import asyncio
import logging
import schedule
import time
from src.bot.daily_report import send_daily_report

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_daily_report():
    logger.info("Starting daily report generation...")
    asyncio.run(send_daily_report())

schedule.every().day.at("00:00").do(run_daily_report)

logger.info("Scheduler started. Daily reports will be sent at midnight (00:00 UTC)")
logger.info("Press Ctrl+C to stop the scheduler")

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
