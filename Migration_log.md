# 🔄 Migration Log: Telethon to Pyrogram

**Objective:** Migrate the entire backend from Telethon to Pyrogram for better performance and stability with large account pools.

---

## 📅 Status: In Progress

### 🛠️ Dependency Changes

| Task | Status | Notes |
| :--- | :--- | :--- |
| **Remove `telethon`** | [ ] | Decommission Telethon |
| **Add `pyrogram`** | [ ] | Core dependency |
| **Add `tgcrypto`** | [ ] | Required for Pyrogram performance (C-layer) |

---

## 📂 File Migration Checklist

### 1. Account Acquisition (`src/seller/account_seller.py`)

| Telethon Method/Class | Pyrogram Method/Class | Status |
| :--- | :--- | :--- |
| `TelegramClient` | `pyrogram.Client` | [ ] |
| `send_code_request` | `send_code` | [ ] |
| `sign_in` flow | **Update `sign_in` logic** | [ ] |
| `edit_2fa` logic | **Update 2FA/Password reset flow** | [ ] |
| `export_session_string` | **Update session string generation** | [ ] |

### 2. Service Delivery (`src/utils/service_delivery_worker.py`)

| Telethon Method/Class | Pyrogram Method/Class | Status |
| :--- | :--- | :--- |
| `TelegramClient` | `Pyrogram Client` | [ ] |
| `JoinChannelRequest` | `join_chat` | [ ] |
| `ImportChatInviteRequest` | **Remove (Pyrogram handles it)** | [ ] |
| `GetMessagesViews` | **Implement using `client.invoke`** | [ ] |
| `send_reaction` | **Update arguments/logic** | [ ] |
| `LeaveChannelRequest` | `leave_chat` | [ ] |
| `telethon.errors.FloodWait` | `pyrogram.errors.FloodWait` | [ ] |

### 3. Account Health (`src/utils/account_status_checker.py`)

| Task | Status | Notes |
| :--- | :--- | :--- |
| **Update ban check logic** | [ ] | Utilize Pyrogram's exception handling and methods for status checks. |

### 4. Database Seeding (`seed_accounts.py`)

| Task | Status | Notes |
| :--- | :--- | :--- |
| **Ensure input format matches** | [ ] | Validate that seeding handles the new Pyrogram session string format. |

---

## 📝 Notes regarding Session Strings

> **CRITICAL:** Telethon session strings (e.g., `1BVts...`) are **incompatible** with Pyrogram session strings.
>
> **Impact:** This requires a **re-login of all existing accounts**.
>
> **Action:** Truncate the `sold_accounts` database table before starting **Phase 2** (the switch to Pyrogram in production) to avoid using invalid sessions.