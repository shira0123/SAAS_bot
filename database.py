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
                total_withdrawn DECIMAL(10, 2) DEFAULT 0.00,
                payout_method VARCHAR(100),
                payout_details TEXT,
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
        
        cursor.execute("""
            INSERT INTO settings (key, value)
            VALUES ('referral_commission', '0.10')
            ON CONFLICT (key) DO NOTHING
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saas_orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                plan_type VARCHAR(50) NOT NULL,
                duration INTEGER NOT NULL,
                views_per_post INTEGER NOT NULL,
                total_posts INTEGER NOT NULL,
                channel_username VARCHAR(255) NOT NULL,
                channel_id BIGINT,
                status VARCHAR(20) DEFAULT 'active',
                delivered_posts INTEGER DEFAULT 0,
                delay_seconds INTEGER DEFAULT 10,
                price DECIMAL(10, 2) NOT NULL,
                promo_code VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saas_rates (
                id SERIAL PRIMARY KEY,
                rate_type VARCHAR(50) UNIQUE NOT NULL,
                price_per_unit DECIMAL(10, 4) NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT INTO saas_rates (rate_type, price_per_unit, description)
            VALUES 
                ('per_view', 0.001, 'Price per single view'),
                ('per_day_view', 0.05, 'Price per view per day'),
                ('per_reaction', 0.002, 'Price per reaction'),
                ('per_day_reaction', 0.08, 'Price per reaction per day')
            ON CONFLICT (rate_type) DO NOTHING
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                discount_type VARCHAR(20) NOT NULL,
                discount_value DECIMAL(10, 2) NOT NULL,
                usage_limit INTEGER DEFAULT 0,
                times_used INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saas_referrals (
                id SERIAL PRIMARY KEY,
                referrer_user_id BIGINT NOT NULL,
                referred_user_id BIGINT NOT NULL,
                referral_code VARCHAR(50) NOT NULL,
                commission_rate DECIMAL(5, 4) DEFAULT 0.05,
                total_earned DECIMAL(10, 2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (referred_user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resellers (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                margin_percentage DECIMAL(5, 2) DEFAULT 10.00,
                total_sales DECIMAL(10, 2) DEFAULT 0.00,
                total_profit DECIMAL(10, 2) DEFAULT 0.00,
                is_active BOOLEAN DEFAULT TRUE,
                approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_usage_logs (
                id SERIAL PRIMARY KEY,
                account_id INTEGER NOT NULL,
                order_id INTEGER NOT NULL,
                channel_username VARCHAR(255),
                action_type VARCHAR(50) NOT NULL,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES sold_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES saas_orders(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                transaction_id VARCHAR(255),
                status VARCHAR(20) DEFAULT 'pending',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                verified_by BIGINT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (verified_by) REFERENCES admins(user_id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promo_code_usage (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                promo_code_id INTEGER NOT NULL,
                code VARCHAR(50) NOT NULL,
                bonus_amount DECIMAL(10, 2) NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id) ON DELETE CASCADE,
                UNIQUE(user_id, promo_code_id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_saas_orders_user ON saas_orders(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_saas_orders_status ON saas_orders(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_account_usage_logs_account ON account_usage_logs(account_id)
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
    
    def get_referral_commission(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'referral_commission'")
        result = cursor.fetchone()
        cursor.close()
        return float(result['value']) if result else 0.10
    
    def set_referral_commission(self, percentage):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES ('referral_commission', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE
            SET value = %s, updated_at = CURRENT_TIMESTAMP
        """, (str(percentage), str(percentage)))
        cursor.close()
        return True
    
    def get_user_detailed_stats(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.first_name,
                u.last_name,
                u.seller_balance,
                u.referral_earnings,
                COALESCE(u.total_withdrawn, 0) as total_withdrawn,
                u.is_banned,
                u.can_withdraw,
                u.created_at,
                COUNT(DISTINCT sa.id) as accounts_sold,
                COUNT(DISTINCT CASE WHEN sa.account_status = 'banned' THEN sa.id END) as banned_accounts,
                COUNT(DISTINCT ref.user_id) as referral_count
            FROM users u
            LEFT JOIN sold_accounts sa ON u.user_id = sa.seller_user_id
            LEFT JOIN users ref ON u.user_id = ref.referred_by
            WHERE u.user_id = %s
            GROUP BY u.user_id
        """, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def get_all_users_stats(self, limit=10, offset=0):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.first_name,
                u.seller_balance,
                u.referral_earnings,
                COALESCE(u.total_withdrawn, 0) as total_withdrawn,
                u.is_banned,
                COUNT(DISTINCT sa.id) as accounts_sold,
                COUNT(DISTINCT ref.user_id) as referral_count
            FROM users u
            LEFT JOIN sold_accounts sa ON u.user_id = sa.seller_user_id
            LEFT JOIN users ref ON u.user_id = ref.referred_by
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_total_users_count(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        cursor.close()
        return result['count'] if result else 0
    
    def get_system_stats(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM users WHERE is_banned = TRUE) as banned_users,
                (SELECT COUNT(*) FROM sold_accounts) as total_accounts_sold,
                (SELECT COUNT(*) FROM sold_accounts WHERE account_status = 'banned') as banned_accounts,
                (SELECT COUNT(*) FROM sold_accounts WHERE account_status = 'active') as active_accounts,
                (SELECT COALESCE(SUM(seller_balance), 0) FROM users) as total_seller_balance,
                (SELECT COALESCE(SUM(total_withdrawn), 0) FROM users) as total_withdrawn,
                (SELECT COALESCE(SUM(referral_earnings), 0) FROM users) as total_referral_earnings,
                (SELECT COUNT(*) FROM withdrawals WHERE status = 'pending') as pending_withdrawals
        """)
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def get_daily_stats(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '24 hours') as new_users_24h,
                (SELECT COUNT(*) FROM sold_accounts WHERE created_at >= NOW() - INTERVAL '24 hours') as new_accounts_24h,
                (SELECT COUNT(*) FROM users WHERE is_banned = TRUE AND updated_at >= NOW() - INTERVAL '24 hours') as new_bans_24h,
                (SELECT COUNT(*) FROM withdrawals WHERE requested_at >= NOW() - INTERVAL '24 hours') as new_withdrawals_24h,
                (SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'approved' AND processed_at >= NOW() - INTERVAL '24 hours') as withdrawn_24h
        """)
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def get_all_accounts(self, limit=50, offset=0):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                id,
                phone_number,
                account_status,
                join_count,
                max_joins,
                is_banned,
                is_full,
                last_used,
                created_at
            FROM sold_accounts
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_account_pool_stats(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_accounts,
                COUNT(CASE WHEN account_status = 'active' AND is_banned = FALSE AND is_full = FALSE THEN 1 END) as active_accounts,
                COUNT(CASE WHEN is_banned = TRUE THEN 1 END) as banned_accounts,
                COUNT(CASE WHEN is_full = TRUE THEN 1 END) as full_accounts
            FROM sold_accounts
        """)
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def add_account_manual(self, phone_number, session_string):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO sold_accounts (seller_user_id, phone_number, session_string, account_status)
            VALUES (0, %s, %s, 'active')
            RETURNING id
        """, (phone_number, session_string))
        result = cursor.fetchone()
        cursor.close()
        return result['id'] if result else None
    
    def remove_account(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM sold_accounts WHERE id = %s", (account_id,))
        cursor.close()
        return True
    
    def update_account_status(self, account_id, status, is_banned=None):
        cursor = self.connection.cursor()
        if is_banned is not None:
            cursor.execute("""
                UPDATE sold_accounts
                SET account_status = %s, is_banned = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, is_banned, account_id))
        else:
            cursor.execute("""
                UPDATE sold_accounts
                SET account_status = %s
                WHERE id = %s
            """, (status, account_id))
        cursor.close()
        return True
    
    def get_account_by_id(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM sold_accounts WHERE id = %s", (account_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def log_account_usage(self, account_id, order_id, channel_username, action_type, success=True, error_message=None):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO account_usage_logs (account_id, order_id, channel_username, action_type, success, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (account_id, order_id, channel_username, action_type, success, error_message))
        cursor.close()
        return True
    
    def get_saas_rates(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM saas_rates ORDER BY id")
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def update_saas_rate(self, rate_type, price_per_unit):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE saas_rates
            SET price_per_unit = %s, updated_at = CURRENT_TIMESTAMP
            WHERE rate_type = %s
        """, (price_per_unit, rate_type))
        cursor.close()
        return True
    
    def create_saas_order(self, user_id, plan_type, duration, views_per_post, total_posts, channel_username, price, promo_code=None):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO saas_orders (user_id, plan_type, duration, views_per_post, total_posts, channel_username, price, promo_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, plan_type, duration, views_per_post, total_posts, channel_username, price, promo_code))
        result = cursor.fetchone()
        cursor.close()
        return result['id'] if result else None
    
    def get_user_orders(self, user_id, limit=10):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM saas_orders
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_active_orders(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM saas_orders
            WHERE status = 'active'
            ORDER BY created_at ASC
        """)
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def is_reseller(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM resellers WHERE user_id = %s AND is_active = TRUE", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    
    def get_reseller_info(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM resellers WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def create_deposit_request(self, user_id, amount, payment_method, transaction_id, status='pending'):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO deposits (user_id, amount, payment_method, transaction_id, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, amount, payment_method, transaction_id, status))
        result = cursor.fetchone()
        cursor.close()
        return result['id'] if result else None
    
    def get_all_admins(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM admins WHERE is_active = TRUE")
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def apply_promo_code(self, user_id, code):
        cursor = self.connection.cursor()
        from datetime import datetime
        
        cursor.execute("""
            SELECT * FROM promo_codes
            WHERE UPPER(code) = UPPER(%s) AND is_active = TRUE
        """, (code,))
        promo = cursor.fetchone()
        
        if not promo:
            cursor.close()
            return {'success': False, 'error': 'Invalid or inactive promo code.'}
        
        if promo.get('expires_at') and promo['expires_at'] < datetime.now():
            cursor.close()
            return {'success': False, 'error': 'This promo code has expired.'}
        
        cursor.execute("""
            SELECT * FROM promo_code_usage
            WHERE user_id = %s AND promo_code_id = %s
        """, (user_id, promo['id']))
        already_used = cursor.fetchone()
        
        if already_used:
            cursor.close()
            return {'success': False, 'error': 'You have already used this promo code.'}
        
        if promo.get('usage_limit', 0) > 0 and promo.get('times_used', 0) >= promo['usage_limit']:
            cursor.close()
            return {'success': False, 'error': 'This promo code has reached its usage limit.'}
        
        bonus_amount = float(promo['discount_value'])
        
        cursor.execute("""
            UPDATE users
            SET buyer_wallet_balance = buyer_wallet_balance + %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING buyer_wallet_balance
        """, (bonus_amount, user_id))
        result = cursor.fetchone()
        new_balance = float(result['buyer_wallet_balance']) if result else 0.00
        
        cursor.execute("""
            INSERT INTO promo_code_usage (user_id, promo_code_id, code, bonus_amount)
            VALUES (%s, %s, %s, %s)
        """, (user_id, promo['id'], code, bonus_amount))
        
        cursor.execute("""
            UPDATE promo_codes
            SET times_used = times_used + 1
            WHERE id = %s
        """, (promo['id'],))
        
        cursor.close()
        return {
            'success': True,
            'bonus_amount': bonus_amount,
            'new_balance': new_balance
        }
    
    def create_promo_code(self, code, discount_type, discount_value, usage_limit=0, expires_at=None):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO promo_codes (code, discount_type, discount_value, usage_limit, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (code, discount_type, discount_value, usage_limit, expires_at))
        result = cursor.fetchone()
        cursor.close()
        return result['id'] if result else None
    
    def delete_promo_code(self, code):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM promo_codes WHERE UPPER(code) = UPPER(%s)", (code,))
        cursor.close()
        return True
    
    def get_all_promo_codes(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_promo_code_usage_logs(self, code=None):
        cursor = self.connection.cursor()
        if code:
            cursor.execute("""
                SELECT pcu.*, u.username
                FROM promo_code_usage pcu
                JOIN users u ON pcu.user_id = u.user_id
                WHERE UPPER(pcu.code) = UPPER(%s)
                ORDER BY pcu.used_at DESC
            """, (code,))
        else:
            cursor.execute("""
                SELECT pcu.*, u.username
                FROM promo_code_usage pcu
                JOIN users u ON pcu.user_id = u.user_id
                ORDER BY pcu.used_at DESC
            """)
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_pending_deposits(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT d.*, u.username
            FROM deposits d
            JOIN users u ON d.user_id = u.user_id
            WHERE d.status = 'pending' OR d.status = 'pending_verification'
            ORDER BY d.created_at ASC
        """)
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def verify_deposit(self, transaction_id, amount, admin_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE deposits
            SET amount = %s, status = 'verified', verified_at = CURRENT_TIMESTAMP, verified_by = %s
            WHERE transaction_id = %s
            RETURNING user_id
        """, (amount, admin_id, transaction_id))
        result = cursor.fetchone()
        
        if result:
            user_id = result['user_id']
            cursor.execute("""
                UPDATE users
                SET buyer_wallet_balance = buyer_wallet_balance + %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (amount, user_id))
        
        cursor.close()
        return result['user_id'] if result else None
    
    def update_order_status(self, order_id, status):
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE saas_orders
            SET status = %s
            WHERE id = %s
        """, (status, order_id))
        cursor.close()
        return True
    
    def get_pending_orders_for_user(self, user_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM saas_orders
            WHERE user_id = %s AND status = 'pending_payment'
            ORDER BY created_at DESC
        """, (user_id,))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_available_accounts(self, limit=100):
        """Get available accounts for service delivery (active, not banned, not full, joins < 500)"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, phone_number, session_string, join_count, max_joins
            FROM sold_accounts
            WHERE account_status = 'active' 
            AND is_banned = FALSE 
            AND is_full = FALSE
            AND join_count < 500
            ORDER BY join_count ASC, last_used ASC NULLS FIRST
            LIMIT %s
        """, (limit,))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def increment_account_join_count(self, account_id):
        """Increment join_count when account joins a channel"""
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sold_accounts
            SET join_count = join_count + 1,
                last_used = CURRENT_TIMESTAMP,
                is_full = CASE WHEN join_count + 1 >= max_joins THEN TRUE ELSE FALSE END
            WHERE id = %s
            RETURNING join_count, is_full
        """, (account_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def update_account_last_used(self, account_id):
        """Update last_used timestamp for an account"""
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sold_accounts
            SET last_used = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (account_id,))
        cursor.close()
        return True
    
    def increment_delivered_posts(self, order_id):
        """Increment delivered_posts count for an order"""
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE saas_orders
            SET delivered_posts = delivered_posts + 1
            WHERE id = %s
            RETURNING delivered_posts
        """, (order_id,))
        result = cursor.fetchone()
        cursor.close()
        return result['delivered_posts'] if result else 0
    
    def get_order_by_id(self, order_id):
        """Get order details by ID"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM saas_orders WHERE id = %s", (order_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def update_order_expiry(self, order_id, expires_at):
        """Set expiration date for an order"""
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE saas_orders
            SET expires_at = %s
            WHERE id = %s
        """, (expires_at, order_id))
        cursor.close()
        return True
    
    def get_expired_orders(self):
        """Get orders that have expired"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM saas_orders
            WHERE status = 'active' 
            AND expires_at IS NOT NULL 
            AND expires_at < CURRENT_TIMESTAMP
            ORDER BY expires_at ASC
        """)
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_user_active_orders(self, user_id):
        """Get active orders for a specific user"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM saas_orders
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
        """, (user_id,))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def get_user_order_history(self, user_id, limit=20):
        """Get order history for a user (completed/expired/cancelled orders)"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM saas_orders
            WHERE user_id = %s AND status IN ('completed', 'expired', 'cancelled')
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def update_order_delay(self, order_id, delay_seconds):
        """Update delay_seconds for an order"""
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE saas_orders
            SET delay_seconds = %s
            WHERE id = %s
        """, (delay_seconds, order_id))
        cursor.close()
        return True
    
    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed")
