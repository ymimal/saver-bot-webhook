import os
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from motor.motor_asyncio import AsyncIOMotorClient
import stripe

app = Flask(__name__)

# ================== CONFIG ==================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
MONGO_DB = os.getenv("MONGO_DB", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# MongoDB Setup
mongo_client = None
premium_collection = None

if MONGO_DB:
    mongo_client = AsyncIOMotorClient(MONGO_DB)
    db = mongo_client.premium
    premium_collection = db.premium_db


async def extend_premium(user_id: int, days: int):
    """Extend or add premium days"""
    if premium_collection is None:
        print("[Webhook] MongoDB not configured. Cannot extend premium.")
        return False

    now = datetime.utcnow()
    data = await premium_collection.find_one({"_id": user_id})

    if data and data.get("expire_date"):
        current_expiry = data["expire_date"]
        if current_expiry < now:
            current_expiry = now
        new_expiry = current_expiry + timedelta(days=days)
    else:
        new_expiry = now + timedelta(days=days)

    await premium_collection.update_one(
        {"_id": user_id},
        {"$set": {"expire_date": new_expiry}},
        upsert=True
    )
    return new_expiry


# ================== SIMPLE WEBSITE ==================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Restricted Saver • Webhook</title>
    <style>
        body { font-family: system-ui; background: #0f172a; color: #e2e8f0; padding: 40px; }
        .container { max-width: 700px; margin: auto; background: #1e2937; padding: 40px; border-radius: 16px; }
        h1 { color: #60a5fa; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Restricted Saver Bot</h1>
        <h2>Stripe Webhook Service (Fixed)</h2>
        <p>Status: <strong style="color:#4ade80">Online</strong></p>
        <p>Webhook Endpoint: <code>/webhook/stripe</code></p>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)


# ================== STRIPE WEBHOOK ==================
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({'error': 'Webhook secret not set'}), 400

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        print(f"[Stripe] Signature verification failed: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})

        user_id_str = metadata.get('user_id')
        plan_key = metadata.get('plan_key')

        if user_id_str and plan_key:
            try:
                user_id = int(user_id_str)
                days_map = {"1month": 30, "3months": 90, "1year": 365}
                days = days_map.get(plan_key, 30)

                # Run async extend_premium
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                new_expiry = loop.run_until_complete(extend_premium(user_id, days))
                loop.close()

                print(f"[Stripe] ✅ Premium extended for user {user_id} by {days} days")
            except Exception as e:
                print(f"[Stripe] Error extending premium: {e}")

    return jsonify({'status': 'success'}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
