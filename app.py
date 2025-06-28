import os
import logging
from datetime import datetime
import pytz
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from sheets import append_action, find_last_start_unmatched, update_duration
from twilio.rest import Client

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

VALID_ACTIONS = {"Walk Start", "Walk End", "Poo", "Pee", "Feed"}

# Set up New York timezone
NY_TIMEZONE = pytz.timezone('America/New_York')

# Twilio credentials (add these to your environment)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'YOUR_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'YOUR_TWILIO_AUTH_TOKEN')

def normalize_action(text: str) -> str:
    """
    Normalize action text to title case for consistent matching.
    Handles various input formats like "walk start", "WALK START", "Walk Start", etc.
    """
    # Convert to lowercase first, then title case
    normalized = text.strip().lower().title()
    
    # Handle special case for "Walk End" (two words)
    if normalized == "Walk End":
        return "Walk End"
    elif normalized == "Walk Start":
        return "Walk Start"
    elif normalized == "Poo":
        return "Poo"
    elif normalized == "Pee":
        return "Pee"
    elif normalized == "Feed":
        return "Feed"
    
    return normalized

def get_ny_time():
    """Get current time in New York timezone"""
    utc_now = datetime.now(pytz.UTC)
    ny_time = utc_now.astimezone(NY_TIMEZONE)
    return ny_time

def get_original_sms_time(message_sid: str):
    """
    Fetch the original time the SMS was sent using Twilio API.
    Returns a datetime object in NY timezone.
    Falls back to current server time if API call fails.
    """
    try:
        # Log credential status for debugging
        logging.info(f"TWILIO_ACCOUNT_SID present: {bool(TWILIO_ACCOUNT_SID and TWILIO_ACCOUNT_SID != 'YOUR_TWILIO_ACCOUNT_SID')}")
        logging.info(f"TWILIO_AUTH_TOKEN present: {bool(TWILIO_AUTH_TOKEN and TWILIO_AUTH_TOKEN != 'YOUR_TWILIO_AUTH_TOKEN')}")
        
        # Log masked values for debugging
        if TWILIO_ACCOUNT_SID:
            logging.info(f"TWILIO_ACCOUNT_SID starts with: {TWILIO_ACCOUNT_SID[:10]}...")
        if TWILIO_AUTH_TOKEN:
            logging.info(f"TWILIO_AUTH_TOKEN starts with: {TWILIO_AUTH_TOKEN[:10]}...")
        
        # Check if we're reading from .env or environment
        logging.info(f"Environment check - TWILIO_ACCOUNT_SID from os.getenv: {bool(os.getenv('TWILIO_ACCOUNT_SID'))}")
        logging.info(f"Environment check - TWILIO_AUTH_TOKEN from os.getenv: {bool(os.getenv('TWILIO_AUTH_TOKEN'))}")
        
        if not TWILIO_ACCOUNT_SID or TWILIO_ACCOUNT_SID == 'YOUR_TWILIO_ACCOUNT_SID':
            raise ValueError("TWILIO_ACCOUNT_SID not properly configured")
        if not TWILIO_AUTH_TOKEN or TWILIO_AUTH_TOKEN == 'YOUR_TWILIO_AUTH_TOKEN':
            raise ValueError("TWILIO_AUTH_TOKEN not properly configured")
            
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages(message_sid).fetch()
        
        # Log available fields for debugging
        logging.info(f"Twilio message fields: {list(msg.__dict__.keys())}")
        logging.info(f"Message status: {getattr(msg, 'status', 'N/A')}")
        logging.info(f"Message date_created: {getattr(msg, 'date_created', 'N/A')}")
        logging.info(f"Message date_sent: {getattr(msg, 'date_sent', 'N/A')}")
        logging.info(f"Message date_updated: {getattr(msg, 'date_updated', 'N/A')}")
        
        # Try different timestamp fields in order of preference
        timestamp = None
        if hasattr(msg, 'date_sent') and msg.date_sent:
            timestamp = msg.date_sent
            logging.info(f"Using date_sent: {timestamp}")
        elif hasattr(msg, 'date_created') and msg.date_created:
            timestamp = msg.date_created
            logging.info(f"Using date_created: {timestamp}")
        elif hasattr(msg, 'date_updated') and msg.date_updated:
            timestamp = msg.date_updated
            logging.info(f"Using date_updated: {timestamp}")
        
        if timestamp is None:
            logging.warning("No timestamp field available in Twilio message, falling back to server time")
            return get_ny_time()
            
        # Convert to NY timezone
        utc_dt = timestamp.replace(tzinfo=pytz.UTC)
        ny_time = utc_dt.astimezone(NY_TIMEZONE)
        logging.info(f"Successfully fetched original SMS time: {ny_time}")
        return ny_time
        
    except Exception as e:
        logging.warning(f"Failed to fetch original SMS time from Twilio API: {e}. Falling back to server time.")
        return get_ny_time()

@app.route("/", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "timestamp": get_ny_time().isoformat()}

@app.route("/sms", methods=["POST"])
def sms_webhook():
    try:
        body = request.form.get("Body", "").strip()
        message_sid = request.form.get("MessageSid")
        if not message_sid:
            raise ValueError("Missing MessageSid in request.")
        
        # Normalize the action for case-insensitive matching
        normalized_body = normalize_action(body)
        
        # Use Twilio API to get the original sent time
        now = get_original_sms_time(message_sid)
        logging.info(f"Incoming SMS body: {body!r} -> normalized: {normalized_body!r}")
        
        resp = MessagingResponse()
        # before any logic, log your env:
        logging.info(f"Using SPREADSHEET_ID={os.getenv('SPREADSHEET_ID')}, creds base64? {bool(os.getenv('GOOGLE_CREDENTIALS_JSON'))}")

        print(f"Received SMS: '{body}' -> '{normalized_body}' at {now}")

        if normalized_body not in VALID_ACTIONS:
            logging.warning(f"Unrecognized command received: {body!r} -> {normalized_body!r}")
            resp.message(f"Unrecognized command. Use one of: {', '.join(VALID_ACTIONS)}.")
            return Response(str(resp), mimetype="application/xml")

        if normalized_body == "Walk End":
            logging.info("Processing Walk End command")
            last = find_last_start_unmatched()
            if not last:
                logging.warning("No active walk found to end")
                resp.message("No active walk found to end.")
                return Response(str(resp), mimetype="application/xml")
            # parse last timestamp - assume it's also in NY timezone
            last_ts = datetime.strptime(f"{last['date']} {last['time']}", "%m/%d/%Y %H:%M")
            last_ts = NY_TIMEZONE.localize(last_ts)
            duration_min = int((now - last_ts).total_seconds() // 60)
            logging.info(f"Walk duration calculated: {duration_min} minutes")
            append_action("Walk End", now, str(duration_min))
            resp.message(f"Walk End logged at {now.strftime('%-I:%M %p')}. Duration: {duration_min} min.")
        else:
            logging.info(f"Processing {normalized_body} command")
            append_action(normalized_body, now)
            resp.message(f"{normalized_body} logged at {now.strftime('%-I:%M %p')}.")

        return Response(str(resp), mimetype="application/xml")
    except Exception as e:
        logging.error(f"Error in sms_webhook: {e}", exc_info=True)
        print(f"Error in sms_webhook: {e}")
        resp = MessagingResponse()
        resp.message(f"Error processing request: {str(e)}")
        return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    logging.info("Starting Flask app...")
    print("Starting Flask app...")
    print(f"SPREADSHEET_ID: {os.getenv('SPREADSHEET_ID')}")
    print(f"GOOGLE_CREDENTIALS_JSON_PATH: {os.getenv('GOOGLE_CREDENTIALS_JSON_PATH')}")
    
    # Debug Twilio credentials
    print(f"TWILIO_ACCOUNT_SID present: {bool(os.getenv('TWILIO_ACCOUNT_SID'))}")
    print(f"TWILIO_AUTH_TOKEN present: {bool(os.getenv('TWILIO_AUTH_TOKEN'))}")
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    if twilio_sid:
        print(f"TWILIO_ACCOUNT_SID starts with: {twilio_sid[:10]}...")
    if twilio_token:
        print(f"TWILIO_AUTH_TOKEN starts with: {twilio_token[:10]}...")
    
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
