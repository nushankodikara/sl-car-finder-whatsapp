"""
This module handles all PocketBase interactions for the car finder bot.
"""
import os
from typing import Dict, List, Optional
import logging
from datetime import datetime
from dotenv import load_dotenv
from pocketbase import PocketBase

# Load environment variables
load_dotenv()

class PocketBaseClient:
    def __init__(self):
        """Initialize PocketBase client."""
        self.client = PocketBase(os.getenv('PB_URL'))
        self.user_data = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with PocketBase using user credentials."""
        try:
            # Authenticate as regular user
            self.user_data = self.client.collection("users").auth_with_password(
                os.getenv('PB_EMAIL'),
                os.getenv('PB_PASSWORD')
            )
            
            if self.user_data.is_valid:
                logging.info("Successfully authenticated with PocketBase")
                logging.info(f"Auth token: {self.client.auth_store.token}")
            else:
                logging.error("Authentication successful but token is invalid")
                raise Exception("Invalid authentication token")
                
        except Exception as e:
            logging.error(f"Failed to authenticate with PocketBase: {e}")
            raise

    def get_or_create_user(self, wa_id: str, profile_name: str) -> Dict:
        """
        Get existing WhatsApp user or create a new one.
        
        Args:
            wa_id (str): WhatsApp ID
            profile_name (str): User's WhatsApp profile name
            
        Returns:
            Dict: User record
        """
        try:
            # Try to find existing user
            user = self.client.collection('whatsapp_users').get_first_list_item(f'wa_id = "{wa_id}"')
            logging.info(f"Found existing user: {wa_id}")
            return user
        except Exception:
            # Create new user if not found
            logging.info(f"Creating new user: {wa_id}")
            user = self.client.collection('whatsapp_users').create({
                "wa_id": wa_id,
                "profile_name": profile_name,
                "last_interaction": datetime.utcnow().isoformat(),
                "total_searches": 0,
                "current_page": 1,
                "status": "active",
                "created": datetime.utcnow().isoformat(),
                "updated": datetime.utcnow().isoformat()
            })
            return user

    def log_message(self, 
                   user_id: str, 
                   content: str, 
                   message_type: str, 
                   command_type: Optional[str] = None,
                   search_query: Optional[str] = None,
                   search_results: Optional[Dict] = None) -> Dict:
        """
        Log a message in the message_logs collection.
        
        Args:
            user_id (str): PocketBase ID of the WhatsApp user
            content (str): Message content
            message_type (str): 'incoming' or 'outgoing'
            command_type (str, optional): Type of command
            search_query (str, optional): Search term if it's a search command
            search_results (Dict, optional): Search results if it's a search command
            
        Returns:
            Dict: Created message log record
        """
        try:
            message_data = {
                "user": user_id,
                "content": content,
                "message_type": message_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if command_type:
                message_data["command_type"] = command_type
            if search_query:
                message_data["search_query"] = search_query
            if search_results:
                message_data["search_results"] = search_results
                
            return self.client.collection('message_logs').create(message_data)
        except Exception as e:
            logging.error(f"Failed to log message: {e}")
            raise

    def update_user_interaction(self, 
                              user_id: str, 
                              search_query: Optional[str] = None,
                              increment_searches: bool = False,
                              current_page: Optional[int] = None) -> Dict:
        """
        Update user's last interaction and optionally other fields.
        
        Args:
            user_id (str): PocketBase ID of the WhatsApp user
            search_query (str, optional): Latest search query
            increment_searches (bool): Whether to increment total_searches
            current_page (int, optional): Current page number for pagination
            
        Returns:
            Dict: Updated user record
        """
        try:
            update_data = {
                "last_interaction": datetime.utcnow().isoformat(),
                "updated": datetime.utcnow().isoformat()
            }
            
            if search_query:
                update_data["last_search_query"] = search_query
            
            if current_page:
                update_data["current_page"] = current_page
            
            if increment_searches:
                user = self.client.collection('whatsapp_users').get_one(user_id)
                current_searches = user.total_searches or 0
                update_data["total_searches"] = current_searches + 1
            
            return self.client.collection('whatsapp_users').update(user_id, update_data)
        except Exception as e:
            logging.error(f"Failed to update user interaction: {e}")
            raise

    def search_vehicles(self, 
                       filters: Optional[str] = None, 
                       sort: str = '-created',
                       page: int = 1,
                       per_page: int = 30) -> Dict:
        """
        Search for vehicles with optional filtering and sorting.
        
        Args:
            filters (str, optional): Filter string in PocketBase format
            sort (str): Sort string (default: '-created' for newest first)
            page (int): Page number for pagination
            per_page (int): Number of items per page
            
        Returns:
            Dict: Response containing vehicle listings
        """
        try:
            return self.client.collection('vehicle_listings').get_list(
                page=page,
                per_page=per_page,
                filter=filters,
                sort=sort
            )
        except Exception as e:
            logging.error(f"Error searching vehicles: {e}")
            raise

    def get_vehicle_by_id(self, vehicle_id: str) -> Dict:
        """
        Get a specific vehicle by its ID.
        
        Args:
            vehicle_id (str): The ID of the vehicle to retrieve
            
        Returns:
            Dict: Vehicle details
        """
        try:
            return self.client.collection('vehicle_listings').get_one(vehicle_id)
        except Exception as e:
            logging.error(f"Error getting vehicle {vehicle_id}: {e}")
            raise

    def search_vehicles_by_price_range(self, min_price: float, max_price: float) -> List[Dict]:
        """
        Search for vehicles within a specific price range.
        
        Args:
            min_price (float): Minimum price
            max_price (float): Maximum price
            
        Returns:
            List[Dict]: List of matching vehicles
        """
        filter_str = f'pricing >= {min_price} && pricing <= {max_price}'
        try:
            results = self.client.collection('vehicle_listings').get_list(
                filter=filter_str,
                sort='pricing'
            )
            return results.items
        except Exception as e:
            logging.error(f"Error searching vehicles by price range: {e}")
            raise

    def search_vehicles_by_location(self, location: str) -> List[Dict]:
        """
        Search for vehicles in a specific location.
        
        Args:
            location (str): Location to search for
            
        Returns:
            List[Dict]: List of matching vehicles
        """
        filter_str = f'location ~ "{location}"'
        try:
            results = self.client.collection('vehicle_listings').get_list(
                filter=filter_str,
                sort='-created'
            )
            return results.items
        except Exception as e:
            logging.error(f"Error searching vehicles by location: {e}")
            raise

    def search_vehicles_by_title(self, title: str, page: int = 1) -> Dict:
        """
        Search for vehicles by title and return latest 5 matches.
        
        Args:
            title (str): Title to search for
            page (int): Page number for pagination
            
        Returns:
            Dict: Search results containing items and pagination info
        """
        if not self.user_data or not self.user_data.is_valid:
            logging.warning("Authentication token expired, attempting to re-authenticate")
            self._authenticate()
            
        try:
            # Split the search terms and create filter conditions
            search_terms = title.lower().split()
            filter_conditions = []
            
            # Create a condition for each search term
            for term in search_terms:
                filter_conditions.append(f'title ~ "{term}"')
            
            # Combine all conditions with AND operator
            filter_str = " && ".join(filter_conditions)
            
            # Using the correct parameter names as per documentation
            results = self.client.collection('vehicle_listings').get_list(
                page,  # page number
                5,    # per_page (items per page)
                {
                    "filter": filter_str,
                    "sort": "-posted_date"
                }
            )
            return {
                'items': results.items,
                'total_pages': results.total_pages,
                'total_items': results.total_items,
                'page': results.page
            }
        except Exception as e:
            logging.error(f"Error searching vehicles by title: {e}")
            raise

    def format_search_results(self, results: Dict) -> str:
        """
        Format search results into a readable WhatsApp message.
        
        Args:
            results (Dict): Search results containing items and pagination info
            
        Returns:
            str: Formatted message
        """
        if not results['items']:
            return "No vehicles found matching your search criteria."
        
        message_parts = []
        
        # Add header with total results
        message_parts.append(f"Found {results['total_items']} vehicles (showing page {results['page']} of {results['total_pages']})\n")
        
        # Add each vehicle
        for vehicle in results['items']:
            # Access Record object fields using dot notation
            message_parts.append(
                f"🚗 *{vehicle.title}*\n"
                f"💰 Rs. {vehicle.pricing:,} | 🛣️ {vehicle.mileage:,}km\n"
                f"📅 {vehicle.posted_date}\n"
                f"🔗 {vehicle.link}\n"
            )
        
        # Add pagination info if there are more pages
        if results['total_pages'] > 1:
            message_parts.append(f"\nSend 'next' to see more results.")
        
        return "\n".join(message_parts)

# Create a global instance
pb_client = PocketBaseClient() 