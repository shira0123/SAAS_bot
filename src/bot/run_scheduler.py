import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import asyncio
import logging
import schedule
import time
from src.bot.daily_report import send_daily_report
from src.database.database import Database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_daily_report():
    logger.info("Starting daily report generation...")
    asyncio.run(send_daily_report())

def reset_daily_limits():
    """Resets daily delivery counts for Limited plans at midnight."""
    logger.info("🔄 Starting Daily Limit Reset...")
    try:
        db = Database()
        cursor = db.connection.cursor()
        
        # Reset counter for all active limited plans
        cursor.execute("""
            UPDATE saas_orders 
            SET daily_delivery_count = 0, last_delivery_date = CURRENT_DATE 
            WHERE plan_type LIKE '%limited%' AND status = 'active'
        """)
        
        logger.info("✅ Daily limits reset successfully.")
        db.connection.close()
    except Exception as e:
        logger.error(f"❌ Failed to reset daily limits: {e}")

# Schedule Daily Report
schedule.every().day.at("00:00").do(run_daily_report)

# Schedule Daily Quota Reset (Critical for Limited Plans)
schedule.every().day.at("00:00").do(reset_daily_limits)

logger.info("Scheduler started.")
logger.info("- Daily Reports: 00:00 UTC")
logger.info("- Daily Limit Reset: 00:00 UTC")
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