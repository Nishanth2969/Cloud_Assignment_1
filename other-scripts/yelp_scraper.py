import requests
import json
import time
import os
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YelpScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.yelp.com/v3/businesses/search"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_restaurants(self, cuisine: str, location: str = "Manhattan, NY", 
                          limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        params = {
            'term': f'{cuisine} restaurants',
            'location': location,
            'categories': 'restaurants',
            'limit': limit,
            'offset': offset,
            'sort_by': 'rating'
        }
        
        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            businesses = data.get('businesses', [])
            
            restaurants = []
            for business in businesses:
                restaurant = self.format_restaurant_data(business)
                if restaurant:
                    restaurants.append(restaurant)
            
            logger.info(f"Found {len(restaurants)} {cuisine} restaurants")
            return restaurants
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {cuisine} restaurants: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return []
    
    def format_restaurant_data(self, business: Dict[str, Any]) -> Dict[str, Any]:
        try:
            location = business.get('location', {})
            coordinates = business.get('coordinates', {})
            
            return {
                'business_id': business.get('id', ''),
                'name': business.get('name', ''),
                'address': self.format_address(location),
                'coordinates': {
                    'latitude': coordinates.get('latitude', 0.0),
                    'longitude': coordinates.get('longitude', 0.0)
                },
                'review_count': business.get('review_count', 0),
                'rating': business.get('rating', 0.0),
                'zip_code': location.get('zip_code', ''),
                'phone': business.get('phone', ''),
                'categories': [cat.get('title', '') for cat in business.get('categories', [])],
                'price': business.get('price', ''),
                'url': business.get('url', ''),
                'image_url': business.get('image_url', ''),
                'is_closed': business.get('is_closed', False),
                'inserted_at_timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Error formatting restaurant data: {str(e)}")
            return None
    
    def format_address(self, location: Dict[str, Any]) -> str:
        address_parts = []
        
        if location.get('address1'):
            address_parts.append(location['address1'])
        if location.get('address2'):
            address_parts.append(location['address2'])
        if location.get('city'):
            address_parts.append(location['city'])
        if location.get('state'):
            address_parts.append(location['state'])
        if location.get('zip_code'):
            address_parts.append(location['zip_code'])
        
        return ', '.join(address_parts)
    
    def scrape_cuisine_with_pagination(self, cuisine: str, target_count: int = 200) -> List[Dict[str, Any]]:
        all_restaurants = []
        offset = 0
        limit = 50
        
        while len(all_restaurants) < target_count:
            restaurants = self.search_restaurants(cuisine, offset=offset, limit=limit)
            
            if not restaurants:
                logger.warning(f"No more restaurants found for {cuisine} at offset {offset}")
                break
            
            all_restaurants.extend(restaurants)
            offset += limit
            
            time.sleep(0.1)
            
            if offset >= 1000:
                logger.warning(f"Reached Yelp API limit for {cuisine}")
                break
        
        unique_restaurants = self.remove_duplicates(all_restaurants)
        logger.info(f"Collected {len(unique_restaurants)} unique {cuisine} restaurants")
        
        return unique_restaurants[:target_count]
    
    def remove_duplicates(self, restaurants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_ids = set()
        unique_restaurants = []
        
        for restaurant in restaurants:
            business_id = restaurant.get('business_id')
            if business_id and business_id not in seen_ids:
                seen_ids.add(business_id)
                unique_restaurants.append(restaurant)
        
        return unique_restaurants

def scrape_all_cuisines(api_key: str, output_file: str = 'data/restaurants.json'):
    cuisines = [
        'Italian',
        'Chinese',
        'Japanese',
        'Mexican',
        'Indian',
        'American',
        'French',
        'Thai'
    ]
    
    scraper = YelpScraper(api_key)
    all_restaurants = []
    
    for cuisine in cuisines:
        logger.info(f"Scraping {cuisine} restaurants...")
        restaurants = scraper.scrape_cuisine_with_pagination(cuisine, target_count=200)
        all_restaurants.extend(restaurants)
        
        time.sleep(1)
    
    unique_restaurants = scraper.remove_duplicates(all_restaurants)
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(unique_restaurants, f, indent=2)
    
    logger.info(f"Scraped {len(unique_restaurants)} unique restaurants")
    logger.info(f"Data saved to {output_file}")
    
    cuisine_counts = {}
    for restaurant in unique_restaurants:
        categories = restaurant.get('categories', [])
        for category in categories:
            cuisine_counts[category] = cuisine_counts.get(category, 0) + 1
    
    logger.info("Cuisine distribution:")
    for cuisine, count in sorted(cuisine_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"  {cuisine}: {count}")
    
    return unique_restaurants

def main():
    api_key = os.environ.get('YELP_API_KEY')
    if not api_key:
        logger.error("YELP_API_KEY environment variable not set")
        logger.info("Please set your Yelp API key: export YELP_API_KEY='your_api_key_here'")
        return
    
    try:
        restaurants = scrape_all_cuisines(api_key)
        logger.info(f"Successfully scraped {len(restaurants)} restaurants")
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    main()
