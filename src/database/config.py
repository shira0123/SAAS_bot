import os
from dotenv import load_dotenv

load_dotenv()

# --- UPDATED BOT TOKENS ---
# Bot 1: The Acquisition (Seller) Bot
SELLER_BOT_TOKEN = os.getenv('SELLER_BOT_TOKEN')

# Bot 2: The Service (Buyer) Bot
BUYER_BOT_TOKEN = os.getenv('BUYER_BOT_TOKEN')

# --- REMOVED ---
# BOT_TOKEN = os.getenv('BOT_TOKEN') # This is no longer needed

# --- SHARED CREDENTIALS ---
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
DATABASE_URL = os.getenv('DATABASE_URL')

ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

# --- SHARED SETTINGS ---
ACCOUNT_PRICE = float(os.getenv('ACCOUNT_PRICE', '10.00'))
MIN_WITHDRAWAL = float(os.getenv('MIN_WITHDRAWAL', '5.00'))
REFERRAL_COMMISSION = float(os.getenv('REFERRAL_COMMISSION', '0.10'))