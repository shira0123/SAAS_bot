import os
from src.database.database import Database
from src.database.config import ADMIN_IDS

def setup_admins():
    db = Database()
    
    print("Setting up admin users...")
    
    for admin_id in ADMIN_IDS:
        try:
            cursor = db.connection.cursor()
            cursor.execute("""
                INSERT INTO admins (user_id, role, is_active)
                VALUES (%s, 'admin', TRUE)
                ON CONFLICT (user_id) DO UPDATE
                SET is_active = TRUE, role = 'admin'
                RETURNING user_id
            """, (admin_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                print(f"✅ Admin user {admin_id} configured successfully")
        except Exception as e:
            print(f"❌ Error setting up admin {admin_id}: {e}")
    
    print("\nAdmin setup complete!")
    db.close()

if __name__ == "__main__":
    setup_admins()
