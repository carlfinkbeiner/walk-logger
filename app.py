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

def get_ny_time():
    """Get current time in New York timezone"""
    utc_now = datetime.now(pytz.UTC)
    ny_time = utc_now.astimezone(NY_TIMEZONE)
    return ny_time

def get_original_sms_time(message_sid: str):
    """
    Fetch the original time the SMS was sent using Twilio API.
    Returns a datetime object in NY timezone.
    """
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    msg = client.messages(message_sid).fetch()
    # msg.date_sent is in UTC
    if msg.date_sent is None:
        raise ValueError("Twilio message has no date_sent field.")
    utc_dt = msg.date_sent.replace(tzinfo=pytz.UTC)
    return utc_dt.astimezone(NY_TIMEZONE)

@app.route("/sms", methods=["POST"])
def sms_webhook():
    try:
        body = request.form.get("Body", "").strip()
        message_sid = request.form.get("MessageSid")
        if not message_sid:
            raise ValueError("Missing MessageSid in request.")
        # Use Twilio API to get the original sent time
        now = get_original_sms_time(message_sid)
        logging.info(f"Incoming SMS body: {body!r}")
        
        resp = MessagingResponse()
        # before any logic, log your env:
        logging.info(f"Using SPREADSHEET_ID={os.getenv('SPREADSHEET_ID')}, creds base64? {bool(os.getenv('GOOGLE_CREDENTIALS_JSON'))}")

        print(f"Received SMS: '{body}' at {now}")

        if body not in VALID_ACTIONS:
            logging.warning(f"Unrecognized command received: {body!r}")
            resp.message(f"Unrecognized command. Use one of: {', '.join(VALID_ACTIONS)}.")
            return Response(str(resp), mimetype="application/xml")

        if body == "Walk End":
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
            logging.info(f"Processing {body} command")
            append_action(body, now)
            resp.message(f"{body} logged at {now.strftime('%-I:%M %p')}.")

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
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
