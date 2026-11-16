"""A Flask endpoint that verifies TeachMeHIPAA webhook Deliveries.

    pip install flask
    TMH_WEBHOOK_SECRET=... flask --app examples/webhook_server run --port 8000

Register `https://<your host>/webhooks/tmh` as a Webhook subscription's
endpoint, then send it a Test delivery with `webhook_subscriptions.test`.
Locally, a tunnel such as `ngrok http 8000` gives you a public HTTPS URL.
"""

import logging
import os

from flask import Flask, request

from teachmehipaa import Webhook, WebhookSignatureError
from teachmehipaa.types import (
    EventLearnerCertified,
    EventLearnerExpiring,
    TestDelivery,
)

SIGNING_SECRET = os.environ["TMH_WEBHOOK_SECRET"]

app = Flask(__name__)
log = logging.getLogger(__name__)
# Deliveries are retried, so the same Event can arrive twice. A real
# service keeps these in its database.
handled_event_ids: set[str] = set()


@app.post("/webhooks/tmh")
def tmh_webhook() -> tuple[str, int]:
    try:
        event = Webhook.construct_event(
            # The signature covers the raw body and the exact path, query
            # string included.
            request.get_data(),
            request.headers,
            SIGNING_SECRET,
            request.full_path.removesuffix("?"),
        )
    except WebhookSignatureError as error:
        log.warning("rejected a Delivery: %s", error.code)
        return error.code, 400

    if isinstance(event, TestDelivery):
        log.info("Test delivery for %s", event.subscription_id)
        return "ok", 200
    if event.event_id in handled_event_ids:
        return "already handled", 200
    handled_event_ids.add(event.event_id)

    if isinstance(event, EventLearnerCertified):
        log.info("%s is certified", event.data.email)
    elif isinstance(event, EventLearnerExpiring):
        log.info("%s's Certificate expires soon", event.data.email)
    else:
        # Other Event types, including ones added after this version of
        # the library, are acknowledged so they aren't redelivered.
        log.info("ignored %s", event.event_type)
    return "ok", 200
