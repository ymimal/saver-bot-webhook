import os
from flask import Flask, request, jsonify, render_template_string
import stripe
import asyncio

app = Flask(__name__)

# ================== CONFIG ==================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# ==================== SIMPLE WEBSITE ====================
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restricted Saver • Webhook</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 40px 20px; }
        .container { max-width: 720px; margin: 0 auto; background: #1e2937; padding: 50px 40px; border-radius: 20px; }
        h1 { color: #60a5fa; }
        .status { display: inline-flex; align-items: center; background: #334155; padding: 8px 16px; border-radius: 9999px; margin: 20px 0; }
        .dot { width: 10px; height: 10px; background: #4ade80; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }
        code { background: #0f172a; padding: 2px 8px; border-radius: 6px; }
        .endpoint { background: #0f172a; padding: 16px; border-radius: 12px; margin: 20px 0; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Restricted Saver Bot</h1>
        <h2>Stripe Webhook Service</h2>
        
        <div class="status">
            <div class="dot"></div>
            <strong>Online & Ready</strong>
        </div>

        <p>This server receives Stripe payment events and activates premium automatically.</p>

        <div class="endpoint">
            <strong>Webhook URL:</strong><br>
            <code>https://your-app.onrender.com/webhook/stripe</code>
        </div>

        <p><strong>Setup Steps:</strong></p>
        <ol>
            <li>Set <code>STRIPE_WEBHOOK_SECRET</code> in Render Environment Variables</li>
            <li>Add this URL in Stripe Dashboard → Webhooks</li>
            <li>Select event: <code>checkout.session.completed</code></li>
        </ol>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)


# ==================== STRIPE WEBHOOK ====================
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    if not STRIPE_WEBHOOK_SECRET:
        return jsonify({'error': 'STRIPE_WEBHOOK_SECRET not set'}), 400

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        print(f"[Stripe] Signature error: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})

        user_id = metadata.get('user_id')
        plan_key = metadata.get('plan_key')

        if user_id and plan_key:
            days = {"1month": 30, "3months": 90, "1year": 365}.get(plan_key, 30)
            print(f"[Stripe] Payment successful! User: {user_id}, Plan: {plan_key}, Days: {days}")
            # TODO: Add your MongoDB code here to extend premium

    return jsonify({'status': 'success'}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
