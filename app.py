import os
from flask import Flask, request, jsonify, render_template_string
from config import STRIPE_WEBHOOK_SECRET
from devgagan.modules.stripe_payments import verify_stripe_webhook, handle_successful_payment
import asyncio

app = Flask(__name__)

# ==================== SIMPLE WEBSITE ====================
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restricted Saver • Webhook</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        
        body {
            font-family: 'Inter', system_ui, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 720px;
            margin: 0 auto;
            background: #1e2937;
            border-radius: 20px;
            padding: 50px 40px;
            box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
        }
        h1 { color: #60a5fa; margin-bottom: 10px; }
        .status {
            display: inline-flex;
            align-items: center;
            background: #334155;
            padding: 8px 16px;
            border-radius: 9999px;
            font-size: 14px;
            margin: 20px 0;
        }
        .dot { 
            width: 10px; height: 10px; 
            background: #4ade80; 
            border-radius: 50%; 
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: .4; }
        }
        code {
            background: #0f172a;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.9em;
        }
        .endpoint {
            background: #0f172a;
            padding: 16px;
            border-radius: 12px;
            margin: 20px 0;
            font-family: monospace;
        }
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

        <p>This server receives Stripe payment events and automatically activates premium for users.</p>

        <div class="endpoint">
            <strong>Webhook URL:</strong><br>
            <code>https://your-app.onrender.com/webhook/stripe</code>
        </div>

        <p><strong>How to connect:</strong></p>
        <ol>
            <li>Copy the webhook URL above</li>
            <li>Go to Stripe Dashboard → Developers → Webhooks</li>
            <li>Add endpoint and paste the URL</li>
            <li>Select event: <code>checkout.session.completed</code></li>
        </ol>

        <p style="margin-top: 40px; font-size: 13px; color: #64748b;">
            Powered by Stripe • Made for Restricted Saver Bot
        </p>
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

    event = verify_stripe_webhook(payload, sig_header)
    if event is None:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_successful_payment(event))
            loop.close()
        except Exception as e:
            print(f"[Stripe Webhook Error] {e}")

    return jsonify({'status': 'success'}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
