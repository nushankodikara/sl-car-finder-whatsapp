"""
This module contains response templates and message handling logic for the WhatsApp bot.
"""
from .pocketbase import pb_client
import logging
from .query_parser import TokenType

# Dictionary of greeting messages and their variations
GREETING_MESSAGES = {
    "hello": ["hi", "hello", "hey", "start"],
}

# Response templates
RESPONSES = {
    "greeting": (
        "Hello! 👋 Welcome to the SL Car Finder bot.\n\n"
        "I can help you find cars using natural language queries. Just tell me what you're looking for!\n\n"
        "🔍 Basic Search:\n"
        "- find toyota aqua\n"
        "- find honda civic\n"
        "- find bmw\n\n"
        "💰 Price Filters:\n"
        "- find aqua higher than 5,000,000\n"
        "- find civic lower than 8,000,000\n"
        "- find prius between 6,000,000 - 9,000,000\n\n"
        "🚗 Car Condition:\n"
        "- find new toyota prius\n"
        "- find used honda fit\n"
        "- find second hand aqua\n\n"
        "🔄 Combined Filters:\n"
        "- find new toyota aqua between 5,000,000 - 8,000,000\n"
        "- find used honda civic higher than 7,000,000\n"
        "- find prius lower than 6,500,000\n\n"
        "💡 Tips:\n"
        "- Start your query with 'find'\n"
        "- Use natural language (e.g., 'higher than', 'lower than', 'between')\n"
        "- Combine multiple conditions in one query\n"
        "- Send 'next' to see more results\n\n"
        "Try any of these examples or create your own query!"
    ),
    "unknown": "I'm not sure how to respond to that. Send 'hi' for help.",
    "no_search_term": "Please provide what car you're looking for.\nExample: find toyota aqua",
    "no_previous_search": "You haven't performed a search yet. Please start with 'find' followed by the car name.",
    "end_of_results": "You've reached the end of the search results. Try a new search with 'find'."
}

def get_message_type(message: str) -> tuple:
    """
    Determine the type of message received and extract any search terms.
    
    Args:
        message (str): The message text received from the user
        
    Returns:
        tuple: (message_type, search_term)
    """
    message = message.lower().strip()
    
    # Check if message is a greeting
    if message in GREETING_MESSAGES["hello"]:
        return "greeting", None
    
    # Check if it's a car search request
    if message.startswith("find "):
        search_term = message[5:].strip()  # Remove 'find ' from the start
        if search_term:
            return "car_search", search_term
        return "no_search_term", None
    
    # Check if it's a next page request
    if message == "next":
        return "next_page", None
        
    return "unknown", None

def generate_response(message: str, user_id: str = None) -> str:
    """
    Generate an appropriate response based on the message type.
    
    Args:
        message (str): The message text received from the user
        user_id (str, optional): The PocketBase ID of the user
        
    Returns:
        str: The response message to send back
    """
    message_type, search_term = get_message_type(message)
    
    if message_type == "car_search":
        # Search for cars and format results
        results = pb_client.search_vehicles_by_title(search_term)
        return pb_client.format_search_results(results)
    
    elif message_type == "next_page" and user_id:
        try:
            # Get user's last search info
            user = pb_client.client.collection('whatsapp_users').get_one(user_id)
            if not user.last_search_query:
                return RESPONSES["no_previous_search"]
            
            # Get next page of results
            current_page = (user.current_page or 1) + 1
            results = pb_client.search_vehicles_by_title(user.last_search_query, current_page)
            
            # Check if we've reached the end of results
            if not results['items']:
                return RESPONSES["end_of_results"]
                
            return pb_client.format_search_results(results)
            
        except Exception as e:
            logging.error(f"Error handling next page request: {e}")
            return RESPONSES["unknown"]
    
    return RESPONSES.get(message_type, RESPONSES["unknown"]) 