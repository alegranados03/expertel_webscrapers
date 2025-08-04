import re
import time
from datetime import datetime, timedelta
from threading import Lock

from flask import Flask, jsonify, request

app = Flask(__name__)

# Thread-safe storage for codes
code_storage = {"code": None, "timestamp": None, "used": False}
code_lock = Lock()

# Code expiration time (5 minutes)
CODE_EXPIRATION_MINUTES = 5


@app.route("/sms", methods=["POST"])
def receive_sms():
    global code_storage

    try:
        data = request.get_json()

        # Log the raw payload for debugging
        print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] Raw payload: {data}")

        # Handle both old format (key) and new format (nested structure)
        raw_message = None
        sender_phone = "unknown"

        if data and "key" in data:
            # Old format for backward compatibility
            raw_message = data["key"]
        elif data and "data" in data and "payload" in data["data"] and "text" in data["data"]["payload"]:
            # New format: extract text from nested structure
            payload = data["data"]["payload"]
            raw_message = payload["text"]
            sender_phone = payload.get("from", {}).get("phone_number", "unknown")
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Formato de mensaje no reconocido")
            return jsonify({"error": "Message format not recognized"}), 400

        print(f"📩 [{datetime.now().strftime('%H:%M:%S')}] SMS desde {sender_phone}: {raw_message}")

        # Buscar un número de 6-8 dígitos en cualquier parte del mensaje
        # Bell usa códigos de 8 dígitos según el ejemplo: 91721285
        match = re.search(r"\b(\d{6,8})\b", raw_message)

        if match:
            code = match.group(1)

            with code_lock:
                code_storage = {"code": code, "timestamp": datetime.now(), "used": False}

            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Código 2FA capturado: {code} (desde {sender_phone})")
            return jsonify(
                {
                    "status": "code saved",
                    "code": code,
                    "timestamp": code_storage["timestamp"].isoformat(),
                    "from": sender_phone,
                }
            )

        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] No se encontró código de 6-8 dígitos en: {raw_message}")
        return jsonify({"status": "no code found in message"})

    except Exception as e:
        print(f"💥 [{datetime.now().strftime('%H:%M:%S')}] Error procesando SMS: {str(e)}")
        return jsonify({"error": f"Error processing SMS: {str(e)}"}), 500


@app.route("/code", methods=["GET"])
def get_code():
    global code_storage

    with code_lock:
        if not code_storage["code"]:
            return jsonify({"code": None, "status": "no code available"})

        # Check if code has expired
        if code_storage["timestamp"]:
            time_diff = datetime.now() - code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired"})

        # Check if code was already used
        if code_storage["used"]:
            return jsonify({"code": None, "status": "code already used"})

        return jsonify(
            {
                "code": code_storage["code"],
                "timestamp": code_storage["timestamp"].isoformat() if code_storage["timestamp"] else None,
                "status": "available",
            }
        )


@app.route("/code/consume", methods=["POST"])
def consume_code():
    """Mark the current code as used and return it"""
    global code_storage

    with code_lock:
        if not code_storage["code"] or code_storage["used"]:
            return jsonify({"code": None, "status": "no code available or already used"})

        # Check if code has expired
        if code_storage["timestamp"]:
            time_diff = datetime.now() - code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired"})

        # Mark as used and return
        code = code_storage["code"]
        code_storage["used"] = True

        print(f"🎯 [{datetime.now().strftime('%H:%M:%S')}] Código consumido: {code}")
        return jsonify(
            {
                "code": code,
                "status": "consumed",
                "timestamp": code_storage["timestamp"].isoformat() if code_storage["timestamp"] else None,
            }
        )


@app.route("/status", methods=["GET"])
def get_status():
    """Get current webhook status"""
    with code_lock:
        return jsonify(
            {
                "webhook_active": True,
                "has_code": bool(code_storage["code"]),
                "code_timestamp": code_storage["timestamp"].isoformat() if code_storage["timestamp"] else None,
                "code_used": code_storage["used"],
                "server_time": datetime.now().isoformat(),
            }
        )


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    print(f"🚀 SMS 2FA Webhook iniciado en puerto 8000")
    print(f"📱 Endpoints disponibles:")
    print(f"   POST /sms - Recibir SMS")
    print(f"   GET /code - Obtener código disponible")
    print(f"   POST /code/consume - Consumir código")
    print(f"   GET /status - Estado del webhook")
    print(f"   GET /health - Health check")
    app.run(host="0.0.0.0", port=8000, debug=False)
