# Walk Logger Testing Guide

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export SPREADSHEET_ID="your-google-spreadsheet-id"
   export SHEET_NAME="Sheet1"  # or your sheet name
   export PORT="5000"
   ```

3. **Verify Google Sheets Setup**
   - Ensure your Google service account has access to the spreadsheet
   - The spreadsheet should have columns: Date, Time, Action, Duration

## Testing Steps

### 1. Local Testing (Recommended First)

**Start the Flask app:**
```bash
python app.py
```

**In another terminal, run the test script:**
```bash
python test_app.py
```

This will test all actions locally without needing Twilio.

### 2. Twilio Webhook Testing

**Option A: Using ngrok (Recommended)**
```bash
# Install ngrok if you haven't
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start your Flask app
python app.py

# In another terminal, expose your local server
ngrok http 5000
```

**Option B: Deploy to a cloud service**
- Heroku, Railway, or similar
- Update your Twilio webhook URL to point to your deployed app

### 3. Twilio Configuration

1. **Log into Twilio Console**
2. **Go to Phone Numbers → Manage → Active numbers**
3. **Click on your number**
4. **Set the webhook URL:**
   - For ngrok: `https://your-ngrok-url.ngrok.io/sms`
   - For deployed app: `https://your-app-url.com/sms`
5. **Set HTTP method to POST**

### 4. Manual Testing

**Text these commands to your Twilio number:**
- `Walk Start`
- `Pee`
- `Poo`
- `Feed`
- `Walk End`

**Expected responses:**
- ✅ Valid actions: Confirmation with timestamp
- ❌ Invalid actions: Error message listing valid options

## Troubleshooting

### Common Issues:

1. **"No active walk found to end"**
   - You need to send "Walk Start" before "Walk End"

2. **Google Sheets errors**
   - Check your service account permissions
   - Verify SPREADSHEET_ID is correct
   - Ensure the sheet exists and is accessible

3. **Twilio not receiving responses**
   - Check webhook URL is correct
   - Verify your app is accessible from the internet
   - Check Twilio logs for errors

4. **Local testing fails**
   - Ensure Flask app is running on port 5000
   - Check all environment variables are set
   - Verify credentials file exists

### Debug Mode

Add this to your Flask app for more detailed logging:
```python
app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
```

## Verification

After testing, check your Google Sheet to verify:
1. Actions are being logged with correct timestamps
2. Walk durations are calculated correctly
3. Data is in the expected format (Date, Time, Action, Duration) 