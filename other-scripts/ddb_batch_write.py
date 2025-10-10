import boto3
import json
import logging
from typing import List, Dict, Any
from decimal import Decimal
import os
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamoDBLoader:
    def __init__(self, table_name: str, region: str = 'us-east-1'):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        
    def convert_floats_to_decimal(self, obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self.convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_floats_to_decimal(v) for v in obj]
        return obj
    
    def prepare_item_for_dynamodb(self, restaurant: Dict[str, Any]) -> Dict[str, Any]:
        item = self.convert_floats_to_decimal(restaurant.copy())
        
        required_fields = {
            'business_id': item.get('business_id', ''),
            'name': item.get('name', ''),
            'address': item.get('address', ''),
            'coordinates': item.get('coordinates', {'latitude': 0, 'longitude': 0}),
            'review_count': item.get('review_count', 0),
            'rating': item.get('rating', Decimal('0.0')),
            'zip_code': item.get('zip_code', ''),
            'inserted_at_timestamp': item.get('inserted_at_timestamp', 0)
        }
        
        optional_fields = {
            'phone': item.get('phone', ''),
            'categories': item.get('categories', []),
            'price': item.get('price', ''),
            'url': item.get('url', ''),
            'image_url': item.get('image_url', ''),
            'is_closed': item.get('is_closed', False)
        }
        
        final_item = {**required_fields, **optional_fields}
        
        for key, value in final_item.items():
            if value == '' and key not in ['business_id', 'name']:
                final_item[key] = None
        
        return final_item
    
    def batch_write_items(self, items: List[Dict[str, Any]], batch_size: int = 25):
        total_items = len(items)
        successful_writes = 0
        failed_writes = 0
        
        logger.info(f"Starting batch write of {total_items} items to {self.table_name}")
        
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            
            try:
                with self.table.batch_writer() as batch_writer:
                    for item in batch:
                        prepared_item = self.prepare_item_for_dynamodb(item)
                        batch_writer.put_item(Item=prepared_item)
                        successful_writes += 1
                
                logger.info(f"Successfully wrote batch {i//batch_size + 1}/{(total_items-1)//batch_size + 1}")
                
            except ClientError as e:
                logger.error(f"Error writing batch {i//batch_size + 1}: {e}")
                failed_writes += len(batch)
            except Exception as e:
                logger.error(f"Unexpected error in batch {i//batch_size + 1}: {e}")
                failed_writes += len(batch)
        
        logger.info(f"Batch write completed. Success: {successful_writes}, Failed: {failed_writes}")
        return successful_writes, failed_writes
    
    def upsert_restaurants(self, restaurants: List[Dict[str, Any]]):
        logger.info(f"Upserting {len(restaurants)} restaurants to DynamoDB")
        
        valid_restaurants = []
        for restaurant in restaurants:
            if restaurant.get('business_id') and restaurant.get('name'):
                valid_restaurants.append(restaurant)
            else:
                logger.warning(f"Skipping restaurant with missing business_id or name: {restaurant}")
        
        if not valid_restaurants:
            logger.error("No valid restaurants to upsert")
            return 0, 0
        
        return self.batch_write_items(valid_restaurants)
    
    def get_table_info(self):
        try:
            response = self.table.describe()
            item_count = response['Table']['ItemCount']
            table_size = response['Table']['TableSizeBytes']
            
            logger.info(f"Table: {self.table_name}")
            logger.info(f"Item count: {item_count}")
            logger.info(f"Table size: {table_size} bytes")
            
            return {
                'item_count': item_count,
                'table_size': table_size,
                'table_status': response['Table']['TableStatus']
            }
        except ClientError as e:
            logger.error(f"Error getting table info: {e}")
            return None

def create_sample_data(count: int = 100) -> List[Dict[str, Any]]:
    import random
    import time
    
    cuisines = ['Italian', 'Chinese', 'Japanese', 'Mexican', 'Indian']
    sample_restaurants = []
    
    for i in range(count):
        cuisine = random.choice(cuisines)
        restaurant = {
            'business_id': f'sample-restaurant-{i+1}',
            'name': f'Sample {cuisine} Restaurant {i+1}',
            'address': f'{random.randint(1, 999)} Sample St, Manhattan, NY {random.randint(10001, 10999)}',
            'coordinates': {
                'latitude': round(40.7128 + random.uniform(-0.1, 0.1), 6),
                'longitude': round(-74.0060 + random.uniform(-0.1, 0.1), 6)
            },
            'review_count': random.randint(10, 500),
            'rating': round(random.uniform(3.0, 5.0), 1),
            'zip_code': str(random.randint(10001, 10999)),
            'phone': f'+1{random.randint(2000000000, 9999999999)}',
            'categories': [cuisine, 'Restaurants'],
            'price': random.choice(['$', '$$', '$$$', '$$$$']),
            'url': f'https://www.yelp.com/biz/sample-restaurant-{i+1}',
            'image_url': f'https://example.com/image-{i+1}.jpg',
            'is_closed': random.choice([True, False]),
            'inserted_at_timestamp': time.time()
        }
        sample_restaurants.append(restaurant)
    
    return sample_restaurants

def load_from_file(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            logger.info(f"Loaded {len(data)} restaurants from {file_path}")
            return data
        else:
            logger.error(f"Expected list in {file_path}, got {type(data)}")
            return []
    
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from {file_path}: {e}")
        return []

def main():
    table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'yelp-restaurants')
    
    loader = DynamoDBLoader(table_name)
    
    data_file = 'data/restaurants.json'
    
    if os.path.exists(data_file):
        logger.info(f"Loading restaurants from {data_file}")
        restaurants = load_from_file(data_file)
    else:
        logger.warning(f"Data file {data_file} not found, creating sample data")
        restaurants = create_sample_data(100)
        
        os.makedirs('data', exist_ok=True)
        with open(data_file, 'w') as f:
            json.dump(restaurants, f, indent=2)
        logger.info(f"Sample data saved to {data_file}")
    
    if restaurants:
        success_count, fail_count = loader.upsert_restaurants(restaurants)
        
        if success_count > 0:
            logger.info("Getting updated table information...")
            loader.get_table_info()
        
        logger.info(f"Operation completed. {success_count} successful, {fail_count} failed")
    else:
        logger.error("No restaurant data to load")

if __name__ == "__main__":
    main()
