import logging
import re
import time
from datetime import datetime, timedelta
from threading import Lock

from flask import Flask, jsonify, request

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread-safe storage for codes
code_storage = {"code": None, "timestamp": None, "used": False}
code_lock = Lock()

# Verizon-specific storage for codes
verizon_code_storage = {"code": None, "timestamp": None, "used": False}
verizon_code_lock = Lock()

# AT&T-specific storage for codes
att_code_storage = {"code": None, "timestamp": None, "used": False}
att_code_lock = Lock()

# T-Mobile-specific storage for codes
tmobile_code_storage = {"code": None, "timestamp": None, "used": False}
tmobile_code_lock = Lock()

# Code expiration time (5 minutes)
CODE_EXPIRATION_MINUTES = 5


@app.route("/sms", methods=["POST"])
def receive_sms():
    global code_storage

    try:
        data = request.get_json()

        # Log the raw payload for debugging
        logger.debug(f"Raw payload received: {data}")

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
            logger.warning("Unrecognized message format")
            return jsonify({"error": "Message format not recognized"}), 400

        logger.info(f"SMS from {sender_phone}: {raw_message}")

        # Buscar un número de 6-8 dígitos en cualquier parte del mensaje
        # Bell usa códigos de 8 dígitos según el ejemplo: 91721285
        match = re.search(r"\b(\d{6,8})\b", raw_message)

        if match:
            code = match.group(1)

            with code_lock:
                code_storage = {"code": code, "timestamp": datetime.now(), "used": False}

            logger.info(f"2FA code captured: {code} (from {sender_phone})")
            return jsonify(
                {
                    "status": "code saved",
                    "code": code,
                    "timestamp": code_storage["timestamp"].isoformat(),
                    "from": sender_phone,
                }
            )

        logger.warning(f"No 6-8 digit code found in: {raw_message}")
        return jsonify({"status": "no code found in message"})

    except Exception as e:
        logger.error(f"Error processing SMS: {str(e)}")
        return jsonify({"error": f"Error processing SMS: {str(e)}"}), 500


@app.route("/verizon/sms", methods=["POST"])
def receive_verizon_sms():
    global verizon_code_storage

    try:
        data = request.get_json()

        # Log the raw payload for debugging
        logger.debug(f"[VERIZON] Raw payload: {data}")

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
            logger.warning("[VERIZON] Unrecognized message format")
            return jsonify({"error": "Message format not recognized"}), 400

        logger.info(f"[VERIZON] SMS from {sender_phone}: {raw_message}")

        # Buscar un número de 6-8 dígitos en cualquier parte del mensaje
        # Verizon también usa códigos de 6-8 dígitos
        match = re.search(r"\b(\d{6,8})\b", raw_message)

        if match:
            code = match.group(1)

            with verizon_code_lock:
                verizon_code_storage = {"code": code, "timestamp": datetime.now(), "used": False}

            logger.info(f"[VERIZON] 2FA code captured: {code} (from {sender_phone})")
            return jsonify(
                {
                    "status": "code saved",
                    "code": code,
                    "timestamp": verizon_code_storage["timestamp"].isoformat(),
                    "from": sender_phone,
                    "carrier": "verizon",
                }
            )

        logger.warning(f"[VERIZON] No 6-8 digit code found in: {raw_message}")
        return jsonify({"status": "no code found in message", "carrier": "verizon"})

    except Exception as e:
        logger.error(f"[VERIZON] Error processing SMS: {str(e)}")
        return jsonify({"error": f"Error processing SMS: {str(e)}", "carrier": "verizon"}), 500


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

        logger.info(f"Code consumed: {code}")
        return jsonify(
            {
                "code": code,
                "status": "consumed",
                "timestamp": code_storage["timestamp"].isoformat() if code_storage["timestamp"] else None,
            }
        )


@app.route("/verizon/code", methods=["GET"])
def get_verizon_code():
    global verizon_code_storage

    with verizon_code_lock:
        if not verizon_code_storage["code"]:
            return jsonify({"code": None, "status": "no code available", "carrier": "verizon"})

        # Check if code has expired
        if verizon_code_storage["timestamp"]:
            time_diff = datetime.now() - verizon_code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                verizon_code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired", "carrier": "verizon"})

        # Check if code was already used
        if verizon_code_storage["used"]:
            return jsonify({"code": None, "status": "code already used", "carrier": "verizon"})

        return jsonify(
            {
                "code": verizon_code_storage["code"],
                "timestamp": (
                    verizon_code_storage["timestamp"].isoformat() if verizon_code_storage["timestamp"] else None
                ),
                "status": "available",
                "carrier": "verizon",
            }
        )


@app.route("/verizon/code/consume", methods=["POST"])
def consume_verizon_code():
    """Mark the current Verizon code as used and return it"""
    global verizon_code_storage

    with verizon_code_lock:
        if not verizon_code_storage["code"] or verizon_code_storage["used"]:
            return jsonify({"code": None, "status": "no code available or already used", "carrier": "verizon"})

        # Check if code has expired
        if verizon_code_storage["timestamp"]:
            time_diff = datetime.now() - verizon_code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                verizon_code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired", "carrier": "verizon"})

        # Mark as used and return
        code = verizon_code_storage["code"]
        verizon_code_storage["used"] = True

        logger.info(f"[VERIZON] Code consumed: {code}")
        return jsonify(
            {
                "code": code,
                "status": "consumed",
                "timestamp": (
                    verizon_code_storage["timestamp"].isoformat() if verizon_code_storage["timestamp"] else None
                ),
                "carrier": "verizon",
            }
        )


@app.route("/att/sms", methods=["POST"])
def receive_att_sms():
    global att_code_storage

    try:
        data = request.get_json()

        # Log the raw payload for debugging
        logger.debug(f"[AT&T] Raw payload: {data}")

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
            logger.warning("[AT&T] Unrecognized message format")
            return jsonify({"error": "Message format not recognized"}), 400

        logger.info(f"[AT&T] SMS from {sender_phone}: {raw_message}")

        # Buscar un número de 6-8 dígitos en cualquier parte del mensaje
        # AT&T también usa códigos de 6-8 dígitos
        match = re.search(r"\b(\d{6,8})\b", raw_message)

        if match:
            code = match.group(1)

            with att_code_lock:
                att_code_storage = {"code": code, "timestamp": datetime.now(), "used": False}

            logger.info(f"[AT&T] 2FA code captured: {code} (from {sender_phone})")
            return jsonify(
                {
                    "status": "code saved",
                    "code": code,
                    "timestamp": att_code_storage["timestamp"].isoformat(),
                    "from": sender_phone,
                    "carrier": "att",
                }
            )

        logger.warning(f"[AT&T] No 6-8 digit code found in: {raw_message}")
        return jsonify({"status": "no code found in message", "carrier": "att"})

    except Exception as e:
        logger.error(f"[AT&T] Error processing SMS: {str(e)}")
        return jsonify({"error": f"Error processing SMS: {str(e)}", "carrier": "att"}), 500


@app.route("/att/code", methods=["GET"])
def get_att_code():
    global att_code_storage

    with att_code_lock:
        if not att_code_storage["code"]:
            return jsonify({"code": None, "status": "no code available", "carrier": "att"})

        # Check if code has expired
        if att_code_storage["timestamp"]:
            time_diff = datetime.now() - att_code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                att_code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired", "carrier": "att"})

        # Check if code was already used
        if att_code_storage["used"]:
            return jsonify({"code": None, "status": "code already used", "carrier": "att"})

        return jsonify(
            {
                "code": att_code_storage["code"],
                "timestamp": att_code_storage["timestamp"].isoformat() if att_code_storage["timestamp"] else None,
                "status": "available",
                "carrier": "att",
            }
        )


@app.route("/att/code/consume", methods=["POST"])
def consume_att_code():
    """Mark the current AT&T code as used and return it"""
    global att_code_storage

    with att_code_lock:
        if not att_code_storage["code"] or att_code_storage["used"]:
            return jsonify({"code": None, "status": "no code available or already used", "carrier": "att"})

        # Check if code has expired
        if att_code_storage["timestamp"]:
            time_diff = datetime.now() - att_code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                att_code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired", "carrier": "att"})

        # Mark as used and return
        code = att_code_storage["code"]
        att_code_storage["used"] = True

        logger.info(f"[AT&T] Code consumed: {code}")
        return jsonify(
            {
                "code": code,
                "status": "consumed",
                "timestamp": att_code_storage["timestamp"].isoformat() if att_code_storage["timestamp"] else None,
                "carrier": "att",
            }
        )


@app.route("/tmobile/sms", methods=["POST"])
def receive_tmobile_sms():
    global tmobile_code_storage

    try:
        data = request.get_json()

        # Log the raw payload for debugging
        logger.debug(f"[T-MOBILE] Raw payload: {data}")

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
            logger.warning("[T-MOBILE] Unrecognized message format")
            return jsonify({"error": "Message format not recognized"}), 400

        logger.info(f"[T-MOBILE] SMS from {sender_phone}: {raw_message}")

        # Buscar un número de 6-8 dígitos en cualquier parte del mensaje
        # T-Mobile también usa códigos de 6-8 dígitos
        match = re.search(r"\b(\d{6,8})\b", raw_message)

        if match:
            code = match.group(1)

            with tmobile_code_lock:
                tmobile_code_storage = {"code": code, "timestamp": datetime.now(), "used": False}

            logger.info(f"[T-MOBILE] 2FA code captured: {code} (from {sender_phone})")
            return jsonify(
                {
                    "status": "code saved",
                    "code": code,
                    "timestamp": tmobile_code_storage["timestamp"].isoformat(),
                    "from": sender_phone,
                    "carrier": "tmobile",
                }
            )

        logger.warning(f"[T-MOBILE] No 6-8 digit code found in: {raw_message}")
        return jsonify({"status": "no code found in message", "carrier": "tmobile"})

    except Exception as e:
        logger.error(f"[T-MOBILE] Error processing SMS: {str(e)}")
        return jsonify({"error": f"Error processing SMS: {str(e)}", "carrier": "tmobile"}), 500


@app.route("/tmobile/code", methods=["GET"])
def get_tmobile_code():
    global tmobile_code_storage

    with tmobile_code_lock:
        if not tmobile_code_storage["code"]:
            return jsonify({"code": None, "status": "no code available", "carrier": "tmobile"})

        # Check if code has expired
        if tmobile_code_storage["timestamp"]:
            time_diff = datetime.now() - tmobile_code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                tmobile_code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired", "carrier": "tmobile"})

        # Check if code was already used
        if tmobile_code_storage["used"]:
            return jsonify({"code": None, "status": "code already used", "carrier": "tmobile"})

        return jsonify(
            {
                "code": tmobile_code_storage["code"],
                "timestamp": (
                    tmobile_code_storage["timestamp"].isoformat() if tmobile_code_storage["timestamp"] else None
                ),
                "status": "available",
                "carrier": "tmobile",
            }
        )


@app.route("/tmobile/code/consume", methods=["POST"])
def consume_tmobile_code():
    """Mark the current T-Mobile code as used and return it"""
    global tmobile_code_storage

    with tmobile_code_lock:
        if not tmobile_code_storage["code"] or tmobile_code_storage["used"]:
            return jsonify({"code": None, "status": "no code available or already used", "carrier": "tmobile"})

        # Check if code has expired
        if tmobile_code_storage["timestamp"]:
            time_diff = datetime.now() - tmobile_code_storage["timestamp"]
            if time_diff > timedelta(minutes=CODE_EXPIRATION_MINUTES):
                tmobile_code_storage = {"code": None, "timestamp": None, "used": False}
                return jsonify({"code": None, "status": "code expired", "carrier": "tmobile"})

        # Mark as used and return
        code = tmobile_code_storage["code"]
        tmobile_code_storage["used"] = True

        logger.info(f"[T-MOBILE] Code consumed: {code}")
        return jsonify(
            {
                "code": code,
                "status": "consumed",
                "timestamp": (
                    tmobile_code_storage["timestamp"].isoformat() if tmobile_code_storage["timestamp"] else None
                ),
                "carrier": "tmobile",
            }
        )


@app.route("/status", methods=["GET"])
def get_status():
    """Get current webhook status"""
    with code_lock, verizon_code_lock, att_code_lock, tmobile_code_lock:
        return jsonify(
            {
                "webhook_active": True,
                "bell": {
                    "has_code": bool(code_storage["code"]),
                    "code_timestamp": code_storage["timestamp"].isoformat() if code_storage["timestamp"] else None,
                    "code_used": code_storage["used"],
                },
                "verizon": {
                    "has_code": bool(verizon_code_storage["code"]),
                    "code_timestamp": (
                        verizon_code_storage["timestamp"].isoformat() if verizon_code_storage["timestamp"] else None
                    ),
                    "code_used": verizon_code_storage["used"],
                },
                "att": {
                    "has_code": bool(att_code_storage["code"]),
                    "code_timestamp": (
                        att_code_storage["timestamp"].isoformat() if att_code_storage["timestamp"] else None
                    ),
                    "code_used": att_code_storage["used"],
                },
                "tmobile": {
                    "has_code": bool(tmobile_code_storage["code"]),
                    "code_timestamp": (
                        tmobile_code_storage["timestamp"].isoformat() if tmobile_code_storage["timestamp"] else None
                    ),
                    "code_used": tmobile_code_storage["used"],
                },
                "server_time": datetime.now().isoformat(),
            }
        )


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    logger.info("SMS 2FA Webhook started on port 8000")
    logger.info("Available endpoints:")
    logger.info("   POST /sms - Receive SMS (Bell)")
    logger.info("   GET /code - Get available code (Bell)")
    logger.info("   POST /code/consume - Consume code (Bell)")
    logger.info("   POST /verizon/sms - Receive SMS (Verizon)")
    logger.info("   GET /verizon/code - Get available code (Verizon)")
    logger.info("   POST /verizon/code/consume - Consume code (Verizon)")
    logger.info("   POST /att/sms - Receive SMS (AT&T)")
    logger.info("   GET /att/code - Get available code (AT&T)")
    logger.info("   POST /att/code/consume - Consume code (AT&T)")
    logger.info("   POST /tmobile/sms - Receive SMS (T-Mobile)")
    logger.info("   GET /tmobile/code - Get available code (T-Mobile)")
    logger.info("   POST /tmobile/code/consume - Consume code (T-Mobile)")
    logger.info("   GET /status - Webhook status")
    logger.info("   GET /health - Health check")
    app.run(host="0.0.0.0", port=8000, debug=False)
