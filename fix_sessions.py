import logging
import os
import sys
from telethon.sessions import StringSession

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_string(s):
    """Aggressively clean string of all non-alphanumeric characters except those used in base64"""
    if not s: return ""
    # Remove all whitespace (spaces, tabs, newlines, non-breaking spaces)
    s = "".join(s.split())
    # Remove any accidental quotes or invisible markers
    s = s.replace('"', '').replace("'", "")
    return s

def fix_sessions():
    db = Database()
    
    print("🔍 Fetching accounts from database...")
    
    # FIXED: Fetch directly to ensure we get the session_string
    cursor = db.connection.cursor()
    cursor.execute("SELECT id, phone_number, session_string FROM sold_accounts")
    accounts = cursor.fetchall()
    cursor.close()
    
    print(f"🔍 Scanning {len(accounts)} accounts...")
    
    fixed_count = 0
    bad_count = 0
    
    for acc in accounts:
        acc_id = acc['id']
        original_session = acc['session_string']
        phone = acc['phone_number']
        
        # 1. Check if it's valid as-is
        try:
            if not original_session:
                raise ValueError("Empty session string")
                
            StringSession(original_session)
            # If no error, it's valid, but let's check if it was 'dirty' (had spaces)
            if original_session != original_session.strip():
                 raise ValueError("Dirty string")
        except (ValueError, Exception):
            # 2. It's invalid. Let's try to fix it.
            cleaned_session = clean_string(original_session)
            
            try:
                # Check if cleaned version works
                StringSession(cleaned_session)
                
                # It works! Update DB.
                print(f"🛠️ Fixing Account #{acc_id} ({phone})...")
                cursor = db.connection.cursor()
                cursor.execute("""
                    UPDATE sold_accounts 
                    SET session_string = %s 
                    WHERE id = %s
                """, (cleaned_session, acc_id))
                fixed_count += 1
                
            except Exception as e:
                print(f"❌ Account #{acc_id} ({phone}) is IRREPARABLE. Error: {e}")
                bad_count += 1

    print("\n" + "="*30)
    print(f"🏁 Scan Complete")
    print(f"✅ Fixed & Updated: {fixed_count}")
    print(f"❌ Still Broken: {bad_count}")
    print(f"✅ Total Healthy: {len(accounts) - bad_count}")
    print("="*30)

if __name__ == "__main__":
    fix_sessions()