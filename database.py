import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(
                os.getenv('DATABASE_URL'),
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = True
            print("Database connected successfully")
        except Exception as e:
            print(f"Database connection error: {e}")
            raise
    
    def init_schema(self):
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                seller_balance DECIMAL(10, 2) DEFAULT 0.00,
                buyer_wallet_balance DECIMAL(10, 2) DEFAULT 0.00,
                referral_code VARCHAR(50) UNIQUE,
                referred_by BIGINT,
                referral_earnings DECIMAL(10, 2) DEFAULT 0.00,
                is_banned BOOLEAN DEFAULT FALSE,
                can_withdraw BOOLEAN DEFAULT TRUE,
                user_type VARCHAR(20) DEFAULT 'seller',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referred_by) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                role VARCHAR(50) DEFAULT 'admin',
                permissions TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sold_accounts (
                id SERIAL PRIMARY KEY,
                seller_user_id BIGINT NOT NULL,
                phone_number VARCHAR(20) NOT NULL,
                session_string TEXT NOT NULL,
                account_status VARCHAR(20) DEFAULT 'active',
                join_count INTEGER DEFAULT 0,
                max_joins INTEGER DEFAULT 100,
                is_banned BOOLEAN DEFAULT FALSE,
                is_full BOOLEAN DEFAULT FALSE,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (seller_user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                withdrawal_method VARCHAR(50) NOT NULL,
                withdrawal_details TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                admin_notes TEXT,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by BIGINT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (processed_by) REFERENCES admins(user_id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_accounts_status ON sold_accounts(account_status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO settings (key, value)
            VALUES ('account_price', '10.00')
            ON CONFLICT (key) DO NOTHING
        """)
        
        cursor.close()
        print("Database schema initialized successfully")
    
    def get_user(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
    def is_admin(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM admins WHERE user_id = %s AND is_active = TRUE", (user_id,))
        admin = cursor.fetchone()
        cursor.close()
        return admin is not None
    
    def update_user_balance(self, user_id, amount, balance_type='seller'):
        cursor = self.connection.cursor()
        field = 'seller_balance' if balance_type == 'seller' else 'buyer_wallet_balance'
        cursor.execute(f"""
            UPDATE users 
            SET {field} = {field} + %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING {field}
        """, (amount, user_id))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def get_user_by_referral(self, referral_code):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE referral_code = %s", (referral_code,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
    def get_user_accounts_count(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM sold_accounts WHERE seller_user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result['count'] if result else 0
    
    def get_user_total_earnings(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(seller_balance + referral_earnings), 0) as total
            FROM users WHERE user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return float(result['total']) if result else 0.0
    
    def get_referral_count(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE referred_by = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result['count'] if result else 0
    
    def create_user(self, user_id, username=None, first_name=None, last_name=None, referral_code=None, referred_by=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING *
            """, (user_id, username, first_name, last_name, referral_code, referred_by))
            user = cursor.fetchone()
            cursor.close()
            return user
        except Exception as e:
            cursor.close()
            print(f"Error creating user: {e}")
            return None
    
    def get_account_price(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'account_price'")
        result = cursor.fetchone()
        cursor.close()
        return float(result['value']) if result else 10.00
    
    def set_account_price(self, price):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES ('account_price', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE
            SET value = %s, updated_at = CURRENT_TIMESTAMP
        """, (str(price), str(price)))
        cursor.close()
        return True
    
    def create_sold_account(self, seller_user_id, phone_number, session_string):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO sold_accounts (seller_user_id, phone_number, session_string, account_status)
            VALUES (%s, %s, %s, 'processing')
            RETURNING id
        """, (seller_user_id, phone_number, session_string))
        result = cursor.fetchone()
        cursor.close()
        return result['id'] if result else None
    
    def mark_account_active(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sold_accounts
            SET account_status = 'active'
            WHERE id = %s
        """, (account_id,))
        cursor.close()
        return True
    
    def update_referral_earnings(self, user_id, amount):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE users
            SET referral_earnings = referral_earnings + %s,
                seller_balance = seller_balance + %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (amount, amount, user_id))
        cursor.close()
        return True
    
    def get_user_stats(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                seller_balance,
                referral_earnings,
                total_withdrawn,
                payout_method,
                payout_details,
                can_withdraw,
                is_banned
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def get_banned_accounts_count(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM sold_accounts 
            WHERE seller_user_id = %s AND account_status = 'banned'
        """, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result['count'] if result else 0
    
    def set_payout_info(self, user_id, method, details):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE users
            SET payout_method = %s,
                payout_details = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (method, details, user_id))
        cursor.close()
        return True
    
    def create_withdrawal(self, user_id, amount, method, details):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO withdrawals (user_id, amount, withdrawal_method, withdrawal_details)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, amount, method, details))
        result = cursor.fetchone()
        cursor.close()
        return result['id'] if result else None
    
    def get_user_withdrawal_count(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM withdrawals 
            WHERE user_id = %s AND status = 'approved'
        """, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result['count'] if result else 0
    
    def get_withdrawal_limits(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'withdrawal_limits'")
        result = cursor.fetchone()
        cursor.close()
        if result:
            return [float(x) for x in result['value'].split(',')]
        return [10.0, 50.0, 100.0, 500.0, 5000.0]
    
    def set_withdrawal_limits(self, limits):
        cursor = self.connection.cursor()
        limits_str = ','.join([str(x) for x in limits])
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES ('withdrawal_limits', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE
            SET value = %s, updated_at = CURRENT_TIMESTAMP
        """, (limits_str, limits_str))
        cursor.close()
        return True
    
    def get_pending_withdrawals(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT w.*, u.username, u.first_name, u.last_name
            FROM withdrawals w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.status = 'pending'
            ORDER BY w.requested_at ASC
        """)
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_withdrawal_by_id(self, withdrawal_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT w.*, u.username, u.first_name, u.last_name, u.seller_balance,
                   u.referral_earnings, u.total_withdrawn, u.payout_method, u.payout_details
            FROM withdrawals w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.id = %s
        """, (withdrawal_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def approve_withdrawal(self, withdrawal_id, admin_id, notes=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = %s", (withdrawal_id,))
            withdrawal = cursor.fetchone()
            
            if not withdrawal:
                cursor.close()
                return False
            
            user_id = withdrawal['user_id']
            amount = withdrawal['amount']
            
            cursor.execute("""
                UPDATE withdrawals
                SET status = 'approved',
                    processed_at = CURRENT_TIMESTAMP,
                    processed_by = %s,
                    admin_notes = %s
                WHERE id = %s
            """, (admin_id, notes, withdrawal_id))
            
            cursor.execute("""
                UPDATE users
                SET seller_balance = seller_balance - %s,
                    total_withdrawn = total_withdrawn + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (amount, amount, user_id))
            
            cursor.close()
            return True
        except Exception as e:
            cursor.close()
            print(f"Error approving withdrawal: {e}")
            return False
    
    def reject_withdrawal(self, withdrawal_id, admin_id, notes=None):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE withdrawals
            SET status = 'rejected',
                processed_at = CURRENT_TIMESTAMP,
                processed_by = %s,
                admin_notes = %s
            WHERE id = %s
        """, (admin_id, notes, withdrawal_id))
        cursor.close()
        return True
    
    def get_user_by_username(self, username):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def ban_user(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE users
            SET is_banned = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))
        cursor.close()
        return True
    
    def unban_user(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE users
            SET is_banned = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))
        cursor.close()
        return True
    
    def set_withdraw_permission(self, user_id, can_withdraw):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE users
            SET can_withdraw = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (can_withdraw, user_id))
        cursor.close()
        return True
    
    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed")
