# Telegram Marketplace Bot - Complete Testing Guide

## ✅ Replit Environment Status
The bot is currently **RUNNING** in the Replit workflow. Check the console logs to monitor bot activity.

## Prerequisites
- A Telegram account you can use for testing
- Access to the bot on Telegram (@YourBotUsername)
- A test phone number (ideally a secondary number for safety)
- Admin access (your user ID must be in ADMIN_IDS)
- **Bot must be running** (check workflow status in Replit)

## Important Notes
⚠️ **CRITICAL**: When selling a Telegram account:
- **The verification code appears in your Telegram app**, not via SMS!
- Check the chat from "Telegram" (official) in your Telegram app
- The code usually arrives within 10-30 seconds
- If you don't see it after 2 minutes, check SMS as fallback

---

## Phase 1 Testing: Foundation & Core Bot Setup

### Test 1.1: Bot Initialization
1. Find your bot on Telegram
2. Send `/start` command
3. ✅ **Expected**: Welcome message appears with seller menu showing 6 buttons:
   - 💰 Sell TG Account
   - 💎 Buyer Menu
   - 💸 Withdraw
   - 👤 Profile
   - 🎁 Refer & Earn
   - 💬 Support

### Test 1.2: User Registration
1. Start bot with `/start`
2. Check that you're registered in the database
3. ✅ **Expected**: Bot remembers you on subsequent `/start` commands

### Test 1.3: Admin Authentication
**Note**: Only works if your user ID is in ADMIN_IDS secret
1. As admin, try admin commands: `/setprice 15.00`
2. ✅ **Expected**: Admin can execute commands
3. Try with non-admin account
4. ✅ **Expected**: Non-admin gets permission denied

---

## Phase 2 Testing: Account Selling Workflow

### Test 2.1: Phone Number Submission
1. Click **💰 Sell TG Account** button
2. Read the information message
3. Send a valid phone number in international format (e.g., `+1234567890`)
4. ✅ **Expected**: 
   - Message: "✅ Verification Code Sent!"
   - Instructions to check Telegram app
   - Bot asks for the 5-digit code

### Test 2.2: Invalid Phone Number Handling
1. Send an invalid phone number (e.g., `12345`)
2. ✅ **Expected**: Error message asking for correct format
3. Send a valid number to continue

### Test 2.3: OTP Verification (Without 2FA)
**IMPORTANT**: Use an account WITHOUT 2FA enabled for this test

1. After receiving "Code sent" message
2. **Open your Telegram app** and check the "Telegram" official chat
3. Copy the 5-digit code
4. Send the code to the bot
5. ✅ **Expected**:
   - "✅ Code verified successfully!"
   - Bot starts processing (3 steps shown)
   - Step 1: Terminating other sessions
   - Step 2: Setting up 2FA security
   - Step 3: Saving account to database
   - Button appears: "✅ I Have Logged Out"

### Test 2.4: Invalid OTP Code
1. During OTP step, send wrong code (e.g., `11111`)
2. ✅ **Expected**: Error message, can retry with correct code
3. Send correct code to continue

### Test 2.5: 2FA Password Verification
**IMPORTANT**: Use an account WITH 2FA enabled for this test

1. Follow phone number and OTP steps
2. After OTP verification
3. ✅ **Expected**: Bot asks for 2FA password
4. Send your 2FA password
5. ✅ **Expected**: Password verified, processing continues
6. Your password message should be deleted for security

### Test 2.6: Session Processing & Payment
1. After seeing "✅ I Have Logged Out" button
2. Verify you're logged out from other devices
3. Click the button
4. ✅ **Expected**:
   - Verification process runs
   - Success message with:
     - 💰 Payout amount
     - 📱 Account ID
     - 📞 Phone number
     - 💵 New balance
   - Returns to main menu

### Test 2.7: Cancellation
1. Start account selling process
2. At any step, send `/cancel`
3. ✅ **Expected**: Process cancelled, returns to main menu

### Test 2.8: Admin Price Control
**Admin only**
1. Send `/setprice 20.00`
2. ✅ **Expected**: Confirmation that price is updated
3. Start selling process again
4. ✅ **Expected**: New price shown in the initial message

---

## Phase 3 Testing: Seller Management & Payouts

### Test 3.1: Profile Section
1. Click **👤 Profile** button
2. ✅ **Expected**: Display shows:
   - Lifetime Earnings
   - Current Balance
   - Total Withdrawn
   - Accounts Sold
   - Banned Accounts
   - Referral Earnings
   - Payout Info (if set)
   - Option to set/update payout info

### Test 3.2: Set Payout Information
1. In Profile, click **💳 Set Payout Info**
2. Select payment method (e.g., UPI)
3. Enter payout details
4. ✅ **Expected**: Payout info saved and shown in profile

### Test 3.3: Withdrawal Request
1. Ensure you have balance > $0
2. Click **💸 Withdraw** button
3. Enter withdrawal amount (must be >= minimum limit)
4. ✅ **Expected**:
   - If valid: Withdrawal request created, admin notified
   - If invalid: Error message with requirements

### Test 3.4: Withdrawal Limits (Progressive)
1. Try first withdrawal with amount below $10
2. ✅ **Expected**: Error (minimum $10 for 1st withdrawal)
3. After 1st successful withdrawal, minimum should be $50
4. Test subsequent limits: $100, $500, $5000

### Test 3.5: Admin Withdrawal Management
**Admin only**
1. After user creates withdrawal request
2. Admin sends `/withdraws pending`
3. ✅ **Expected**: List of pending requests with inline buttons
4. Click a request to view details
5. ✅ **Expected**: User stats, amount, UPI info shown
6. Click **✅ Approve**
7. ✅ **Expected**: 
   - Status → approved
   - Amount deducted from user balance
   - User notified
   - Total withdrawn updated

### Test 3.6: Admin Withdrawal Rejection
1. Admin views pending withdrawal
2. Click **❌ Reject**
3. ✅ **Expected**: Status → rejected, user notified

### Test 3.7: Admin User Controls
**Admin only**
1. `/ban <username>` - Ban a user
2. ✅ **Expected**: User cannot sell accounts or withdraw
3. `/unban <username>` - Unban user
4. ✅ **Expected**: User can use bot normally again
5. `/stopwithdraw <username>` - Block withdrawals
6. ✅ **Expected**: User cannot create withdrawal requests
7. `/allowwithdraw <username>` - Allow withdrawals
8. ✅ **Expected**: User can withdraw again

---

## Phase 4 Testing: Referral System & Admin Reporting

### Test 4.1: Referral Link Generation
1. Click **🎁 Refer & Earn** button
2. ✅ **Expected**: 
   - Unique referral link shown
   - Explanation of commission
   - Current referral stats

### Test 4.2: Referral Signup
1. Copy referral link from User A's account
2. Send link to User B (in a different Telegram account)
3. User B clicks link and starts bot
4. ✅ **Expected**: User B is registered with User A as referrer

### Test 4.3: Referral Commission
1. User B (referred) sells an account
2. Check User A's profile
3. ✅ **Expected**: 
   - User A receives 10% commission (default)
   - Referral earnings updated
   - Balance increased

### Test 4.4: Admin Set Referral Rate
**Admin only**
1. Send `/setref 0.15` (15%)
2. ✅ **Expected**: Commission rate updated
3. Next referral sale should use new rate

### Test 4.5: Support Section
1. Click **💬 Support** button
2. ✅ **Expected**: Support information displayed

### Test 4.6: Admin User Statistics
**Admin only**
1. `/accsell @username` - View specific user stats
2. ✅ **Expected**: Detailed stats for that user
3. `/alluser` - List all users (page 1)
4. ✅ **Expected**: Paginated list with stats
5. Use navigation buttons to see more pages

### Test 4.7: Overall System Stats
**Admin only**
1. Send `/stats`
2. ✅ **Expected**: System-wide statistics:
   - Total users
   - Total accounts sold
   - Banned accounts
   - Total earnings distributed
   - Active accounts
   - And more

### Test 4.8: Daily Automated Report
**Admin only**
1. Wait for midnight (or manually trigger if possible)
2. ✅ **Expected**: 
   - Admin receives daily report
   - Shows 24-hour stats
   - Shows lifetime stats

---

## Phase 5 Testing: SaaS Foundation & Account Pool Manager

### Test 5.1: Buyer Menu Access
1. From main menu, click **💎 Buyer Menu**
2. ✅ **Expected**: Buyer menu shown with 7 buttons:
   - 💎 Buy Plan
   - 💰 Deposit
   - 📋 My Plans
   - 📊 Plan History
   - 🎁 Referral Program
   - 👔 Reseller Panel
   - 💬 Support

### Test 5.2: Buyer UI - Buy Plan
1. In Buyer menu, click **💎 Buy Plan**
2. ✅ **Expected**: Service pricing information shown
   - Per view rates
   - Per day view rates
   - Per reaction rates
   - Per day reaction rates

### Test 5.3: Buyer UI - Deposit
1. Click **💰 Deposit**
2. ✅ **Expected**: Instructions for adding funds shown

### Test 5.4: Buyer UI - My Plans
1. Click **📋 My Plans**
2. ✅ **Expected**: 
   - Shows active service orders
   - Or message if no active plans

### Test 5.5: Buyer UI - Plan History
1. Click **📊 Plan History**
2. ✅ **Expected**: Past orders history displayed

### Test 5.6: Buyer UI - Referral Program
1. Click **🎁 Referral Program**
2. ✅ **Expected**: Buyer-specific referral system info

### Test 5.7: Buyer UI - Reseller Panel
1. Click **👔 Reseller Panel**
2. ✅ **Expected**: Reseller management interface

### Test 5.8: Switch Between Seller/Buyer Menus
1. From Buyer menu, go back to Seller menu
2. From Seller menu, go to Buyer menu
3. ✅ **Expected**: Seamless navigation, balances displayed correctly

### Test 5.9: Admin Account Pool Manager
**Admin only**
1. Send `/accounts` command
2. ✅ **Expected**: 
   - List of all sold accounts
   - Status (Active, Banned, Full)
   - Join count for each
   - Pagination if many accounts

### Test 5.10: Add Account Manually
**Admin only**
1. Click **Add Account** button in account pool
2. Follow prompts to add session string
3. ✅ **Expected**: Account added to pool

### Test 5.11: Remove Account
**Admin only**
1. In account pool, select an account
2. Click **Remove** button
3. ✅ **Expected**: Account removed from pool

### Test 5.12: Account Status Checker
**Automated - Admin only**
1. Wait for scheduled check (every 6 hours)
2. OR manually run the checker if possible
3. ✅ **Expected**: 
   - All accounts checked for ban status
   - Database updated with current status
   - Admin notified of any changes

### Test 5.13: Low Pool Alert
**Automated - Admin only**
1. Ensure active accounts < 100
2. ✅ **Expected**: 
   - Admin receives low pool alert
   - Alert shows current count

---

## Phase 6 Testing: Plan Purchase System (Buy Plan Flow)

### Test 6.1: Access Plan Types
1. From Buyer menu, click **💎 Buy Plan**
2. ✅ **Expected**: Display of 4 plan types:
   - 💎 Unlimited Views
   - 🎯 Limited Views
   - ❤️ Unlimited Reactions
   - 🎪 Limited Reactions
   - Current rates shown
   - Back button available

### Test 6.2: Unlimited Views Plan - Full Flow
1. Click **💎 Unlimited Views**
2. Enter duration (e.g., `30` days)
3. ✅ **Expected**: Accepts valid number (1-365)
4. Enter daily views (e.g., `1000`)
5. ✅ **Expected**: Asks for channel link
6. Enter channel (e.g., `@testchannel` or `https://t.me/testchannel`)
7. ✅ **Expected**: Shows order summary with:
   - Plan details
   - Channel name
   - Duration
   - Daily views
   - Price calculation formula
   - Total price
   - Proceed/Cancel buttons
8. Click **✅ Proceed to Payment**
9. ✅ **Expected**: 
   - Order created successfully
   - Order ID generated
   - Status: Pending Payment
   - Payment instructions displayed

### Test 6.3: Limited Views Plan - Full Flow
1. Click **🎯 Limited Views**
2. Enter duration (e.g., `7` days)
3. Enter daily posts (e.g., `3` posts)
4. Enter views per post (e.g., `500` views)
5. Enter channel username
6. ✅ **Expected**: Order summary shows:
   - Calculation: 7 days × 3 posts/day × 500 views/post × $0.0010
   - Total price calculated correctly
7. Confirm order
8. ✅ **Expected**: Order created with pending_payment status

### Test 6.4: Unlimited Reactions Plan
1. Click **❤️ Unlimited Reactions**
2. Complete flow similar to unlimited views
3. ✅ **Expected**: Uses per_day_reaction rate
4. Verify price calculation is correct

### Test 6.5: Limited Reactions Plan
1. Click **🎪 Limited Reactions**
2. Complete flow similar to limited views
3. ✅ **Expected**: Uses per_reaction rate
4. Verify price calculation is correct

### Test 6.6: Input Validation - Invalid Duration
1. Start any plan purchase
2. Enter invalid duration: `0` or `400` or `abc`
3. ✅ **Expected**: Error message, asks to retry
4. Enter valid number to continue

### Test 6.7: Input Validation - Negative Numbers
1. During daily posts/views step
2. Enter negative number: `-5`
3. ✅ **Expected**: Error message asking for positive number

### Test 6.8: Channel Link Validation
1. Reach channel link step
2. Test various formats:
   - `@yourchannel` ✅
   - `https://t.me/yourchannel` ✅
   - `yourchannel` ✅ (auto-adds @)
   - `t.me/yourchannel` ✅
3. ✅ **Expected**: All formats accepted and normalized to @username

### Test 6.9: Cancel Order Mid-Flow
1. Start any plan purchase
2. At any step, send `/cancel`
3. ✅ **Expected**: 
   - Process cancelled
   - Confirmation message shown
   - Can start new order

### Test 6.10: Cancel at Confirmation Screen
1. Complete all steps to reach order summary
2. Click **❌ Cancel** button
3. ✅ **Expected**: 
   - Order not created
   - Cancellation message shown
   - Returns to buyer menu

### Test 6.11: Price Calculation Accuracy
**Manual verification**
1. Create order with known values:
   - Unlimited Views: 10 days × 100 views × $0.05 = $50.00
   - Limited Views: 5 days × 2 posts × 200 views × $0.001 = $2.00
2. ✅ **Expected**: Calculated price matches manual calculation
3. Check formula displayed matches the calculation

### Test 6.12: Database Order Storage
**Requires database access**
1. After creating an order
2. Query database:
   ```sql
   SELECT * FROM saas_orders WHERE user_id = YOUR_USER_ID ORDER BY id DESC LIMIT 1;
   ```
3. ✅ **Expected**: 
   - Order exists in database
   - Status = 'pending_payment'
   - All details stored correctly
   - Plan type, duration, channel stored
   - Price matches UI calculation

### Test 6.13: Multiple Orders
1. Create first order successfully
2. Return to Buy Plan menu
3. Create second order with different parameters
4. ✅ **Expected**: 
   - Both orders created
   - Different order IDs
   - Both in pending_payment status
   - Can view in database

---

## Phase 7 Testing: Automated Payment Integration

### Test 7.1: Access Deposit Menu
1. From Buyer menu, click **💰 Deposit**
2. ✅ **Expected**: Display showing:
   - Current wallet balance
   - 5 payment methods (UPI, Paytm, Crypto, Binance, Promo Code)
   - Back button

### Test 7.2: UPI Deposit - Complete Flow
**Requires admin access for verification**
1. Click **💳 UPI Payment**
2. ✅ **Expected**: Shows UPI ID and instructions
3. Make a test UPI payment and get UTR number
4. Send UTR number (12-digit format)
5. ✅ **Expected**: 
   - Confirmation message shown to user
   - Admin receives notification with UTR
6. **As Admin**: Run `/deposits` command
7. ✅ **Expected**: See pending deposit in list
8. **As Admin**: Run `/verifydep <utr> <amount>`
9. ✅ **Expected**:
   - Deposit verified
   - User wallet credited
   - User receives confirmation notification
   - If user has pending orders, they activate automatically

### Test 7.3: UPI Deposit - Invalid UTR
1. Start UPI deposit flow
2. Send invalid UTR (wrong length or format)
3. ✅ **Expected**: Error message, asks for correct format

### Test 7.4: Payment Method Placeholders
1. Try **💰 Paytm**
2. ✅ **Expected**: "Coming Soon" message
3. Try **₿ Crypto (CryptoMus)**
4. ✅ **Expected**: "Coming Soon" message  
5. Try **🔶 Binance**
6. ✅ **Expected**: "Coming Soon" message

### Test 7.5: Apply Promo Code - Success
**Requires admin to create code first**
1. **As Admin**: Run `/promo`
2. Click **➕ Create Promo Code**
3. Send: `TEST10 10.00 100 30`
4. ✅ **Expected**: Promo code created successfully
5. **As User**: Go to Deposit menu
6. Click **🎁 Apply Promo Code**
7. Enter code: `TEST10`
8. ✅ **Expected**:
   - Success message
   - Wallet credited with $10.00
   - New balance displayed

### Test 7.6: Apply Promo Code - Already Used
1. Apply same code again (TEST10)
2. ✅ **Expected**: Error "You have already used this promo code"

### Test 7.7: Apply Promo Code - Invalid Code
1. Click Apply Promo Code
2. Enter non-existent code: `INVALID99`
3. ✅ **Expected**: Error "Invalid or inactive promo code"

### Test 7.8: Promo Code Management - Create
**Admin only**
1. Run `/promo`
2. Click **➕ Create Promo Code**
3. Send valid format: `WELCOME20 20.00 50 7`
4. ✅ **Expected**:
   - Code created
   - Shows details: amount, limit, expiry

### Test 7.9: Promo Code Management - Delete
**Admin only**
1. From `/promo` menu, click **❌ Delete Promo Code**
2. Send code name: `TEST10`
3. ✅ **Expected**: Code deleted successfully

### Test 7.10: Promo Code Management - View All
**Admin only**
1. Create several promo codes
2. Run `/promo` → **📊 View All Codes**
3. ✅ **Expected**: List showing:
   - All active codes
   - Usage statistics (used/limit)
   - Expiration dates
   - Status (active/inactive)

### Test 7.11: Promo Code Management - Usage Logs
**Admin only**
1. After users apply codes
2. Run `/promo` → **📜 Usage Logs**
3. ✅ **Expected**: List showing:
   - Username who used code
   - Code name
   - Bonus amount
   - Timestamp

### Test 7.12: Automated Plan Activation - Sufficient Balance
1. **As User**: Create an order (via Buy Plan)
2. Order status: pending_payment
3. Deposit funds (amount ≥ order price)
4. **As Admin**: Verify deposit
5. ✅ **Expected**:
   - Order status → active
   - Payment deducted from wallet
   - User notified of activation
   - New balance shown

### Test 7.13: Automated Plan Activation - Insufficient Balance
1. Create order with price $50
2. Deposit only $30
3. ✅ **Expected**:
   - Wallet credited with $30
   - Order remains pending
   - User notified to add more funds

### Test 7.14: Automated Plan Activation - Multiple Orders
1. Create 3 orders: $10, $20, $30 (total $60)
2. Deposit $35
3. ✅ **Expected**:
   - First two orders activated ($10 + $20)
   - Third order remains pending
   - Balance: $5 remaining
   - User notified about partial activation

### Test 7.15: Admin Deposits Command
**Admin only**
1. Have users submit several UPI deposits
2. Run `/deposits`
3. ✅ **Expected**: List showing:
   - User ID and username
   - Payment method
   - UTR/Transaction ID
   - Status
   - Request timestamp
   - Instructions to verify

### Test 7.16: Deposit Verification - Admin Flow
**Admin only**
1. Run `/deposits` to see pending requests
2. Verify with: `/verifydep 123456789012 50.00`
3. ✅ **Expected**:
   - Success confirmation to admin
   - Shows user details
   - New user balance
   - User receives notification

### Test 7.17: Promo Code Expiration
**Admin only**
1. Create code expiring in 1 day: `EXP5 5.00 10 1`
2. Wait 2 days (or manipulate date in database)
3. Try to apply code
4. ✅ **Expected**: Error "This promo code has expired"

### Test 7.18: Promo Code Usage Limit
**Admin only**
1. Create code with limit 2: `LIMITED 5.00 2 30`
2. Have 2 users apply it successfully
3. Have 3rd user try to apply
4. ✅ **Expected**: Error "reached its usage limit"

### Test 7.19: Cancel Deposit Flow
1. Start any deposit flow (UPI or Promo)
2. Send `/cancel`
3. ✅ **Expected**:
   - Process cancelled
   - Can start new deposit

### Test 7.20: Database Verification - Deposits Table
**Requires database access**
1. After creating deposits
2. Query:
   ```sql
   SELECT * FROM deposits WHERE user_id = YOUR_USER_ID;
   ```
3. ✅ **Expected**:
   - Deposit record exists
   - Correct status
   - Transaction ID stored
   - Timestamps accurate

### Test 7.21: Database Verification - Promo Code Usage
**Requires database access**
1. After applying promo code
2. Query:
   ```sql
   SELECT * FROM promo_code_usage WHERE user_id = YOUR_USER_ID;
   ```
3. ✅ **Expected**:
   - Usage record exists
   - Correct bonus amount
   - Cannot apply same code again (UNIQUE constraint)

---

## Common Issues & Troubleshooting

### Issue 1: "Not receiving verification code"
**Solution**: 
- ✅ Check the official "Telegram" chat in your Telegram app (NOT SMS!)
- Wait 2 minutes before assuming failure
- Ensure phone number is correct
- Check SMS as last resort

### Issue 2: "Session expired" error
**Solution**:
- Start the process again from the beginning
- Don't wait too long between steps

### Issue 3: "Invalid verification code"
**Solution**:
- Make sure you're entering the latest code
- Code must be 5 digits
- Don't include spaces or dashes

### Issue 4: "2FA password incorrect"
**Solution**:
- Ensure you're using the correct 2FA password
- Your password message will be deleted automatically for security

### Issue 5: Withdrawal request not showing
**Solution**:
- Ensure you have set payout information first
- Check minimum withdrawal limits
- Verify you're not banned or withdrawal-blocked

---

## Database Verification Queries
**For developers/admins with database access:**

```sql
-- Check user registration
SELECT * FROM users WHERE user_id = YOUR_USER_ID;

-- Check sold accounts
SELECT * FROM sold_accounts WHERE seller_user_id = YOUR_USER_ID;

-- Check withdrawal requests
SELECT * FROM withdrawals WHERE user_id = YOUR_USER_ID;

-- Check referral relationships
SELECT * FROM users WHERE referred_by = YOUR_USER_ID;

-- Check system settings
SELECT * FROM settings;

-- Check SaaS rates
SELECT * FROM saas_rates;
```

---

## Success Criteria Summary

### Phase 1 ✅
- [x] Bot responds to /start
- [x] User registration works
- [x] Admin authentication works
- [x] Main menu displays correctly

### Phase 2 ✅
- [x] Phone number validation works
- [x] Verification code sent successfully
- [x] **FIXED**: Users can receive and enter OTP codes
- [x] 2FA password handling works
- [x] Account processing completes
- [x] Payment credited correctly
- [x] Admin can set account price

### Phase 3 ✅
- [x] Profile displays user stats
- [x] Payout info can be set
- [x] Withdrawal requests work
- [x] Progressive limits enforced
- [x] Admin can approve/reject withdrawals
- [x] Admin can ban/unban users
- [x] Admin can control withdrawal permissions

### Phase 4 ✅
- [x] Referral links generated
- [x] Referral signup tracking works
- [x] Commission payout works
- [x] Admin can set referral rate
- [x] Support section displays
- [x] Admin reporting commands work
- [x] Daily automated reports work

### Phase 5 ✅
- [x] Buyer menu accessible
- [x] All 7 buyer buttons present
- [x] Service pricing displayed
- [x] Deposit instructions shown
- [x] Plans interfaces work
- [x] Buyer referral program shown
- [x] Reseller panel accessible
- [x] Admin account pool manager works
- [x] Manual account add/remove works
- [x] Automated account status checking works
- [x] Low pool alerts work

### Phase 6 ✅
- [x] Plan types menu displays (4 options)
- [x] Unlimited Views plan flow works
- [x] Limited Views plan flow works
- [x] Unlimited Reactions plan flow works
- [x] Limited Reactions plan flow works
- [x] Input validation works at all steps
- [x] Channel link validation and normalization works
- [x] Price calculation is accurate
- [x] Order summary displays correctly
- [x] Order creation with pending_payment status
- [x] Cancel functionality works
- [x] Orders stored in database correctly

### Phase 7 ✅
- [x] Deposit menu accessible with 5 options
- [x] UPI payment flow works (UTR submission)
- [x] Admin deposit verification works (/verifydep)
- [x] Admin can view pending deposits (/deposits)
- [x] Wallet credited after verification
- [x] Promo code application works
- [x] Promo code validation (one-time use, expiry, limits)
- [x] Admin promo management panel (/promo)
- [x] Create promo codes with custom settings
- [x] Delete promo codes
- [x] View all promo codes and usage logs
- [x] Automated plan activation after deposit
- [x] Multiple order activation with balance check
- [x] User notifications for all actions
- [x] Deposits and promo_code_usage tables working

---

## Phase 8 Testing: Service Delivery Engine

### Test 8.1: Service Delivery Worker - Channel Joining
**Prerequisites**: Have at least one sold account in the database and one active order

1. Run the service delivery worker: `python service_delivery_worker.py`
2. Create an active order (complete purchase flow from Phase 6-7)
3. ✅ **Expected**:
   - Worker detects new active order
   - Worker joins channel with required number of accounts
   - Join count incremented in database
   - Usage logs created for channel_join actions
4. Check database: `SELECT * FROM account_usage_logs WHERE action_type = 'channel_join'`
5. ✅ **Expected**: Logs show successful channel joins

### Test 8.2: Service Delivery - View Delivery (Unlimited Plan)
**Test Setup**: Create an unlimited_views plan

1. Ensure service worker is running
2. Post a new message to the target channel
3. ✅ **Expected**:
   - Worker detects new post
   - Worker delivers views using available accounts
   - Delay respected between each view delivery
   - Usage logs created for view_delivery
4. Check logs: `SELECT * FROM account_usage_logs WHERE action_type = 'view_delivery'`
5. ✅ **Expected**: Number of views matches order's views_per_post setting

### Test 8.3: Service Delivery - View Delivery (Limited Plan)
**Test Setup**: Create a limited_views plan with total_posts=5

1. Ensure service worker is running
2. Post multiple messages to the target channel (more than the limit)
3. ✅ **Expected**:
   - First 5 posts receive view deliveries
   - Posts after the 5th are ignored
   - delivered_posts counter incremented to 5
   - No more deliveries after limit reached
4. Check database: `SELECT delivered_posts FROM saas_orders WHERE id = <order_id>`
5. ✅ **Expected**: delivered_posts = 5 (matches total_posts)

### Test 8.4: Service Delivery - Reaction Delivery
**Test Setup**: Create an unlimited_reactions or limited_reactions plan

1. Ensure service worker is running
2. Post a new message to the target channel
3. ✅ **Expected**:
   - Worker delivers reactions using available accounts
   - Different reactions used (👍, ❤️, 🔥, 👏, 😍)
   - Delay respected between each reaction
   - Usage logs created for reaction_delivery
4. Check Telegram channel to see reactions appear
5. ✅ **Expected**: Reactions visible on the post

### Test 8.5: Plan Management - View My Plans
1. As a buyer with active plans, click **📋 My Plans** button
2. ✅ **Expected**: Display shows all active plans with:
   - Plan type and ID
   - Channel username
   - Start date and expiry date
   - Days left until expiry
   - Progress (delivered/total posts)
   - Current delay setting
   - Price paid
3. Each plan should have 4 buttons:
   - 📊 View Details
   - ⏱️ Change Delay
   - 🔄 Renew Plan
   - ❌ Cancel Plan

### Test 8.6: Plan Management - View Plan Details
1. In My Plans, click **📊 View Details** for a plan
2. ✅ **Expected**: Detailed view shows:
   - Complete plan information
   - Timing details (started, expires, duration)
   - Delivery settings (views per post, total posts, delivered, delay)
   - Financial information (price, promo code if used)
   - Current status
3. Click **🔙 Back to Plans** to return

### Test 8.7: Plan Management - Change Delay Time
1. In My Plans, click **⏱️ Change Delay** for a plan
2. ✅ **Expected**: Bot asks for new delay time (5-60 seconds)
3. Send an invalid value (e.g., `100`)
4. ✅ **Expected**: Error message, asks again
5. Send a valid value (e.g., `15`)
6. ✅ **Expected**:
   - Confirmation message
   - Delay updated in database
   - Future deliveries use new delay
7. Check database: `SELECT delay_seconds FROM saas_orders WHERE id = <order_id>`
8. ✅ **Expected**: delay_seconds = 15

### Test 8.8: Plan Management - Cancel Plan
1. In My Plans, click **❌ Cancel Plan** for a plan
2. ✅ **Expected**: Confirmation prompt appears
3. Click **❌ No, Keep It**
4. ✅ **Expected**: Returns without canceling
5. Click **❌ Cancel Plan** again
6. Click **✅ Yes, Cancel**
7. ✅ **Expected**:
   - Plan status updated to 'cancelled'
   - Confirmation message shown
   - Plan removed from active plans list
8. Check database: `SELECT status FROM saas_orders WHERE id = <order_id>`
9. ✅ **Expected**: status = 'cancelled'

### Test 8.9: Plan History
1. Cancel or wait for a plan to expire
2. Click **📊 Plan History** button
3. ✅ **Expected**: Display shows all completed/expired/cancelled plans with:
   - Plan type and ID
   - Channel username
   - Start date
   - Price
   - Status emoji (✅ completed, ⏰ expired, ❌ cancelled)

### Test 8.10: Expiry Handler - Reminder Notifications
**Test Setup**: Create a plan that expires in 3 days

1. Run the expiry handler: `python plan_expiry_handler.py`
2. Wait for expiry check cycle (or set expiry to be imminent for testing)
3. ✅ **Expected**: User receives notification:
   - At 3 days before expiry
   - At 1 day before expiry
   - On expiry day
4. Each notification should include:
   - Plan details
   - Days until expiry
   - Grace period information
   - Renewal instructions

### Test 8.11: Expiry Handler - Auto-Leave After Grace Period
**Test Setup**: Create a plan and let it expire with 3+ days grace period

1. Ensure expiry handler is running
2. Wait for plan to expire + 3 days (or adjust expiry for testing)
3. ✅ **Expected**:
   - Worker makes all accounts leave the channel
   - join_count decremented for each account
   - Order status changed to 'expired'
   - Usage logs created for channel_leave actions
   - User receives final expiry notification
4. Check database: `SELECT status FROM saas_orders WHERE id = <order_id>`
5. ✅ **Expected**: status = 'expired'
6. Check logs: `SELECT * FROM account_usage_logs WHERE action_type = 'channel_leave' AND order_id = <order_id>`
7. ✅ **Expected**: Leave logs for all accounts that joined

### Test 8.12: Integration Test - Complete Flow
**Full end-to-end test of Phase 8**

1. Seller sells an account (Phases 1-2)
2. Buyer deposits money (Phase 7)
3. Buyer purchases an unlimited_views plan (Phase 6)
4. Plan automatically activates (Phase 7)
5. Service worker joins channel with accounts (Phase 8.1)
6. Post a message to the channel
7. ✅ **Expected**: Views delivered automatically (Phase 8.2)
8. Buyer checks "My Plans" to see delivery progress (Phase 8.3)
9. Buyer changes delay time (Phase 8.3)
10. Post another message
11. ✅ **Expected**: Views delivered with new delay
12. Buyer receives expiry reminders (Phase 8.4)
13. Plan expires and enters grace period
14. After grace period, accounts automatically leave (Phase 8.4)

### Phase 8 Verification Checklist ✅
- [ ] Service delivery worker starts without errors
- [ ] Worker detects and processes active orders
- [ ] Channel joining works for public channels
- [ ] Channel joining handles private channels
- [ ] View delivery works for unlimited plans
- [ ] View delivery works for limited plans with quota
- [ ] Reaction delivery works
- [ ] Delay settings are respected
- [ ] Account usage logs are created
- [ ] My Plans button shows all active plans
- [ ] Plan details view shows complete information
- [ ] Delay change flow works with validation
- [ ] Plan cancellation works with confirmation
- [ ] Plan History shows completed/expired/cancelled plans
- [ ] Expiry reminders sent at correct intervals (3 days, 1 day, on expiry)
- [ ] Auto-leave works after grace period
- [ ] Join counts properly managed (incremented/decremented)
- [ ] Order status updates work (active → expired/cancelled)
- [ ] Database tables updated correctly
- [ ] delay_seconds field added to saas_orders table

---

## Next Steps / Known Limitations

### Working Features ✅
- Complete Phase 1-8 seller side functionality
- Complete Phase 1-8 buyer side functionality
- Automated service delivery (views/reactions to channels)
- Payment integration with UPI and promo codes
- Promo code management for admins
- Plan management interface for buyers
- Automated expiry handling and notifications
- Referral system for both sellers and buyers
- Admin controls and reporting
- Account pool management

### Not Yet Implemented ⚠️
- **Reseller approval workflow**
- **Advanced analytics dashboard**
- **Additional payment methods** (Paytm, Crypto, Binance Pay)
- **Plan renewal automation**

These features are planned for future phases (Phase 9+).

---

## Contact & Support
For issues or questions:
- Contact bot support via the Support button
- Check logs for detailed error messages
- Report bugs to the development team

---

## Phase 9 Testing: Advanced Buyer Features & Reseller Program

### Test 9.1: Buyer Referral Program
1. As a buyer, click **🎁 Referral Program**
2. ✅ **Expected**: Referral menu shows:
   - Your referral link
   - Current commission rate (5%)
   - Referral balance
   - Menu buttons: My Referrals, Referral Earnings, Set Wallet Info, Withdraw Earnings

3. Click **📊 My Referrals**
4. ✅ **Expected**: List of referral earnings (empty if no referrals yet)

### Test 9.2: Buyer Referral Wallet Setup
1. From Referral Program, click **💳 Set Wallet Info**
2. Choose payment method (PayPal/Bank/Crypto)
3. Enter wallet details
4. ✅ **Expected**: Wallet info saved successfully

### Test 9.3: Buyer Referral Withdrawal
1. Ensure you have >$5.00 referral balance
2. Click **💸 Withdraw Earnings**
3. ✅ **Expected**: Shows available balance and minimum
4. Enter withdrawal amount
5. ✅ **Expected**: Request submitted, pending admin approval

### Test 9.4: Admin - Buyer Referral Withdrawal Management
**Admin only**
1. User submits referral withdrawal
2. Admin checks pending withdrawals (needs implementation in admin panel)
3. Approve or reject the request
4. ✅ **Expected**: User's referral balance updated, user notified

### Test 9.5: Reseller Panel Access
1. As regular user (non-reseller), click **👔 Reseller Panel**
2. ✅ **Expected**: Message explaining reseller benefits, contact admin to apply

3. As approved reseller, click **👔 Reseller Panel**
4. ✅ **Expected**: Reseller dashboard shows:
   - Total sales and profit
   - Current margin percentage
   - Menu: Create Plan Link, My Sales, Set Margin, Withdraw Commission

### Test 9.6: Reseller - Create Plan Link
1. As reseller, click **💼 Create Plan Link**
2. ✅ **Expected**: Shows reseller link with current margin
3. Share link with customer
4. ✅ **Expected**: Purchases through link tracked to reseller

### Test 9.7: Reseller - Set Margin
1. Click **⚙️ Set Margin**
2. Enter new margin (5-30%)
3. ✅ **Expected**: Margin updated successfully

4. Try invalid margin (<5% or >30%)
5. ✅ **Expected**: Error message, margin not updated

### Test 9.8: Reseller - Withdraw Commission
1. Click **💸 Withdraw Commission**
2. ✅ **Expected**: Shows profit balance, minimum $10
3. Enter amount
4. ✅ **Expected**: Withdrawal request created, pending admin approval

### Test 9.9: Admin - Reseller Management
**Admin only**
1. Send `/resellermgmt`
2. ✅ **Expected**: Reseller management menu shows:
   - View Resellers
   - Approve Reseller
   - Pending Withdrawals
   - Commission Summary
   - Set Commission Rate

3. Click **👥 View Resellers**
4. ✅ **Expected**: List of all resellers with stats

5. Click **✅ Approve Reseller**
6. Enter user ID to approve
7. ✅ **Expected**: User approved as reseller

### Test 9.10: Admin - Reseller Withdrawals
1. From reseller management, click **💰 Pending Withdrawals**
2. ✅ **Expected**: List of pending reseller withdrawal requests
3. Approve or reject a request
4. ✅ **Expected**: Reseller profit deducted, user notified

### Test 9.11: Admin - Commission Summary
1. From reseller management, click **📊 Commission Summary**
2. ✅ **Expected**: Shows:
   - Current SaaS referral commission rate
   - Top buyer referrers
   - Total referrals and earnings per user

### Test 9.12: Full Referral Flow (End-to-End)
1. User A (referrer) gets referral link from Referral Program
2. User B clicks link and starts bot with referral parameter
3. User B purchases a plan
4. ✅ **Expected**: 
   - User A earns 5% commission
   - Commission added to User A's referral balance
   - Visible in User A's referral earnings

### Test 9.13: Full Reseller Flow (End-to-End)
1. Admin approves User C as reseller
2. User C sets margin to 15%
3. User C creates and shares reseller link
4. Customer purchases plan through reseller link
5. ✅ **Expected**:
   - Sale recorded to reseller
   - Profit (15% margin) added to reseller's profit
   - Reseller can withdraw commission


## Support

For additional testing support or to report issues, refer to the project documentation or contact the development team.

---

## Phase 10 Testing: Advanced Admin Tools & Analytics

### Test 10.1: SaaS Admin Reporting
**Prerequisites**: Must be logged in as admin

1. **Access Reporting Dashboard**:
   - Send `/saasreports` command
   - ✅ **Expected**: Menu with 4 options (Payment Reports, Sales & Usage Stats, Export CSV, Back)

2. **Test Payment Reports**:
   - Click "💳 Payment Reports" → Select "All Payments"
   - ✅ **Expected**: List of up to 50 verified payments
   - Test "Revenue Summary"
   - ✅ **Expected**: Today/Week/Month/Lifetime revenue breakdown

3. **Test CSV Export**:
   - Click "📁 Export CSV" → Select "Sales Report"
   - ✅ **Expected**: CSV file download with timestamped filename

### Test 10.2: Broadcast Messaging
1. Send `/broadcast` command
2. Select "All Users"
3. Send test message
4. ✅ **Expected**: Broadcast Complete with success/fail counts

### Test 10.3: Admin Management (Root Admin Only)
1. Send `/adminmgmt` command
2. Click "➕ Add Admin", enter user ID
3. ✅ **Expected**: Confirmation + new admin receives notification
4. Click "📜 Admin Logs"
5. ✅ **Expected**: Action logged with timestamp

### Test 10.4: Enhanced Daily Reports
1. Run: `python daily_report.py`
2. ✅ **Expected**: Comprehensive report with 5 sections:
   - SaaS Sales & Deposits (Today)
   - Seller Accounts (Today)
   - TG Account Pool Status
   - Overall System Stats
   - Pending Actions

Refer to PHASE_10_GUIDE.md for detailed testing procedures.
