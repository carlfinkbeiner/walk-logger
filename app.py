import os
from datetime import datetime
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from sheets import append_action, find_last_start_unmatched, update_duration

app = Flask(__name__)

VALID_ACTIONS = {"Walk Start", "Walk End", "Poo", "Pee", "Feed"}

@app.route("/sms", methods=["POST"])
def sms_webhook():
    body = request.form.get("Body", "").strip()
    now = datetime.now()
    resp = MessagingResponse()

    if body not in VALID_ACTIONS:
        resp.message(f"Unrecognized command. Use one of: {', '.join(VALID_ACTIONS)}.")
        return Response(str(resp), mimetype="application/xml")

    if body == "Walk End":
        last = find_last_start_unmatched()
        if not last:
            resp.message("No active walk found to end.")
            return Response(str(resp), mimetype="application/xml")
        # parse last timestamp
        last_ts = datetime.strptime(f"{last['date']} {last['time']}", "%m/%d/%Y %H:%M")
        duration_min = int((now - last_ts).total_seconds() // 60)
        append_action("Walk End", now, str(duration_min))
        resp.message(f"Walk End logged at {now.strftime('%-I:%M %p')}. Duration: {duration_min} min.")
    else:
        append_action(body, now)
        resp.message(f"{body} logged at {now.strftime('%-I:%M %p')}.")

    return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
