import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
DATABASE_URL = os.getenv('DATABASE_URL')

ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

ACCOUNT_PRICE = float(os.getenv('ACCOUNT_PRICE', '10.00'))
MIN_WITHDRAWAL = float(os.getenv('MIN_WITHDRAWAL', '5.00'))
REFERRAL_COMMISSION = float(os.getenv('REFERRAL_COMMISSION', '0.10'))
