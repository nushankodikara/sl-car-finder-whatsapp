import logging
from flask import current_app, jsonify
import json
import requests
from .responses import generate_response as get_bot_response
from .pocketbase import pb_client

# from app.services.openai_service import generate_response
import re
from datetime import datetime
import pytz

# Set timezone for WhatsApp API calls
WHATSAPP_TIMEZONE = pytz.timezone('Asia/Colombo')  # GTM+5:30


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response):
    # Use our new response generator instead of uppercase
    return get_bot_response(response)


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        # Add timezone information to the request
        current_time = datetime.now(WHATSAPP_TIMEZONE)
        headers["X-WhatsApp-Timezone"] = WHATSAPP_TIMEZONE.zone

        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    """Process incoming WhatsApp message and handle user tracking."""
    try:
        # Extract user information
        contact = body["entry"][0]["changes"][0]["value"]["contacts"][0]
        wa_id = contact["wa_id"]
        profile_name = contact["profile"]["name"]
        
        # Get or create user profile
        user = pb_client.get_or_create_user(wa_id, profile_name)
        
        # Extract message content
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_body = message["text"]["body"]
        
        # Log incoming message
        pb_client.log_message(
            user_id=user.id,
            content=message_body,
            message_type="incoming",
            command_type=get_command_type(message_body)
        )
        
        # Generate response
        response = get_bot_response(message_body, user.id)
        
        # Update user interaction
        update_user_data = {
            "increment_searches": message_body.lower().startswith("find ")
        }
        
        if message_body.lower().startswith("find "):
            update_user_data["search_query"] = message_body[5:].strip()
            update_user_data["current_page"] = 1
        elif message_body.lower() == "next":
            current_user = pb_client.client.collection('whatsapp_users').get_one(user.id)
            update_user_data["current_page"] = (current_user.current_page or 1) + 1
        
        pb_client.update_user_interaction(user.id, **update_user_data)
        
        # Log outgoing message
        pb_client.log_message(
            user_id=user.id,
            content=response,
            message_type="outgoing",
            command_type=get_command_type(message_body)
        )
        
        # Send response
        data = get_text_message_input(wa_id, response)
        send_message(data)
        
    except Exception as e:
        logging.error(f"Error processing WhatsApp message: {e}")
        raise


def get_command_type(message: str) -> str:
    """Determine the command type from the message."""
    message = message.lower().strip()
    
    if message in ["hi", "hello", "hey", "start"]:
        return "greeting"
    elif message.startswith("find "):
        return "search"
    elif message == "next":
        return "next"
    elif message == "help":
        return "help"
    else:
        return "unknown"


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
