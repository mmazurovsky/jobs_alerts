# Premium Features Testing Guide

This directory contains comprehensive tests for the premium subscription system. You can run both automated integration tests and manual testing with a real test bot.

## 🚀 Quick Setup

### 1. Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Ensure MongoDB is running (for local testing)
# Docker: docker run -d -p 27017:27017 mongo:latest
# Or use MongoDB Atlas for cloud testing
```

### 2. Environment Variables

Create a `.env.test` file **(for integration tests only)**:

```bash
# MongoDB test credentials
MONGO_USER=testuser
MONGO_PASSWORD=testpass
MONGO_DB=jobs_alerts_test

# Telegram bot
TEST_TELEGRAM_BOT_TOKEN=your_test_bot_token
ADMIN_USER_ID=your_telegram_user_id

# Payment secret
PAYMENT_SECRET_KEY=test-payment-secret-key
```

- **Note:** You can also provide these variables directly in your shell environment. The test runner script will use system env variables if set, otherwise it will source `.env.test`.
- **For normal app/dev:** Use `main_project/.env` as usual. **Do not source `.env` for integration tests.**

### 3. Get Your Test Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot: `/newbot`
3. Choose a name ending with "test" (e.g., "MyJobAlertsTestBot")
4. Copy the token to your `.env.test` file

### 4. Get Your User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID for testing

## 🧪 Automated Integration Testing

### Run All Integration Tests

```bash
# Use the provided shell script (recommended)
cd main_project/test_integration
./run_integration_tests.sh
```

- This script will source `.env.test` and run all integration tests with the correct environment.
- You can also set env variables in your shell and run `pytest` directly if you prefer.

### Run Specific Test Classes

```bash
pytest test_premium_integration.py::TestTrialSubscription -v
pytest test_premium_integration.py::TestPremiumSubscription -v
pytest test_premium_integration.py::TestPaymentFlow -v
```

### Test Coverage

The automated tests cover:

- ✅ **Trial Subscriptions**: Auto-creation, limits, expiry
- ✅ **Premium Subscriptions**: Multiple plans, limits, stacking
- ✅ **Payment Flow**: Invoice creation, security, completion
- ✅ **Search Management**: Activation/deactivation, limits
- ✅ **Expiry Handling**: Automatic search deactivation
- ✅ **Payment Recovery**: Orphaned payment handling
- ✅ **Edge Cases**: Corrupted data, concurrency, errors

### Mocking

- **search_jobs_via_scraper** and **check_proxy_connection_via_scraper** are automatically mocked for all integration tests via `conftest.py`.
- You do not need to run the real scraper service for integration tests.

## 🤖 Manual Testing (Interactive Bot)

### Start Test Bot

```bash
# Source .env.test or set env variables in your shell
cd main_project/test_integration
source .env.test
python test_bot_manual.py
```

#### (Optional) Create a shell script for manual bot testing:

Create `run_manual_bot.sh`:
```sh
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [ ! -f .env.test ]; then
  echo ".env.test not found"; exit 1;
fi
set -a; source .env.test; set +a
python test_bot_manual.py
```
Make it executable: `chmod +x run_manual_bot.sh`

### Test Scenarios

#### 1. **New User Trial Flow**
```
1. Start chat with your test bot
2. Use /new → Creates first job + 7-day trial
3. Try /new again → Should show upgrade prompt
4. Use /premium → Shows trial status
```

#### 2. **Premium Upgrade Flow**
```
1. Use /premium → Click upgrade buttons
2. Payment flow appears (mocked in test)
3. After "payment": Can create up to 12 searches
4. Use /list → Shows all searches as active
```

#### 3. **Search Limits Testing**
```
Trial user:   /new (1st) ✅ → /new (2nd) ❌
Premium user: /new (×12) ✅ → /new (13th) ❌
```

#### 4. **Expiry Testing**
```python
# In Python console while test bot runs:
controller = TestBotController()
await controller.setup_expired_user(YOUR_USER_ID)

# Then in Telegram:
# Use /new → Should detect expiry and pause excess searches
# Use /list → Should show only 1 active search
```

### Advanced Test Scenarios

```python
# Setup different user states
await controller.setup_trial_user(USER_ID)
await controller.setup_premium_user(USER_ID, "premium_month") 
await controller.setup_expired_user(USER_ID)

# Simulate payments
await controller.simulate_payment(USER_ID, "premium_month")
await controller.simulate_payment(USER_ID, "premium_week")

# Test background processes
await controller.run_expiry_check()
await controller.run_payment_recovery()

# Clean up
await controller.clear_user_data(USER_ID)
```

## 📊 Test Data Management

### Database Collections Used

```
jobs_alerts_test/
├── job_searches          # Job search configurations
├── user_subscriptions    # Premium subscriptions  
├── payment_transactions  # Payment audit trail
└── sent_jobs            # Sent job notifications
```

### Clean Test Data

```python
# Clean specific user
await test_helper.clear_test_data(user_id)

# Or drop entire test database
# mongo jobs_alerts_test --eval "db.dropDatabase()"
```

## 🔍 Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Common Issues

1. **"TEST_TELEGRAM_BOT_TOKEN required"**
   - Solution: Set environment variable with your test bot token

2. **"Not connected to MongoDB"**
   - Solution: Start MongoDB or check connection string

3. **"Bot not responding"**
   - Solution: Check bot token, ensure bot is not already running

4. **Payment tests failing**
   - Solution: Verify PAYMENT_SECRET_KEY is set for tests

### Inspect Test Data

```python
# Check user subscription
subscription = await container.user_subscription_store.get_user_subscription(user_id)
print(f"Subscription: {subscription}")

# Check active searches
count = await container.job_search_store.get_active_job_count(user_id) 
print(f"Active searches: {count}")

# Check premium status
status = await container.premium_service.get_premium_status(user_id)
print(f"Status: {status}")
```

## 🎯 Test Checklist

Before deploying to production, verify:

- [ ] New users get 7-day trial automatically
- [ ] Trial users limited to 1 job search
- [ ] Premium users can create up to 12 searches  
- [ ] Payment flow works end-to-end
- [ ] Subscription stacking works correctly
- [ ] Expired subscriptions pause excess searches
- [ ] Background expiry processing works
- [ ] Payment recovery handles orphaned payments
- [ ] /premium command shows correct status
- [ ] /list shows active/paused search status
- [ ] Upgrade prompts appear when hitting limits

## 📈 Performance Testing

```python
# Test concurrent job creation
import asyncio

async def test_concurrent_creation():
    tasks = []
    for i in range(5):
        task = premium_service.check_user_can_create_job(user_id)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    print(f"Concurrent results: {results}")

# Test large search counts
await test_helper.create_test_job_searches(user_id, 50)
```

## 💡 Tips

- **Use separate test bot**: Never test on production bot
- **Test database**: Always use separate test database
- **Mock payments**: Payment flow is mocked for testing
- **Real Telegram**: Bot interactions are real Telegram messages
- **User ID consistency**: Use same user ID for related tests
- **Clean between tests**: Clear test data to avoid conflicts

Happy testing! 🚀 