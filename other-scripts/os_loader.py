import boto3
import json
import logging
from typing import List, Dict, Any
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenSearchLoader:
    def __init__(self, endpoint: str, region: str = 'us-east-1', index_name: str = 'restaurants'):
        self.endpoint = endpoint
        self.region = region
        self.index_name = index_name
        
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',
            session_token=credentials.token
        )
        
        self.client = OpenSearch(
            hosts=[{'host': endpoint.replace('https://', '').replace('http://', ''), 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=60
        )
    
    def create_index(self):
        index_body = {
            'settings': {
                'index': {
                    'number_of_shards': 1,
                    'number_of_replicas': 0
                }
            },
            'mappings': {
                'properties': {
                    'RestaurantID': {
                        'type': 'keyword'
                    },
                    'Cuisine': {
                        'type': 'keyword'
                    }
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=self.index_name):
                logger.info(f"Index {self.index_name} already exists")
                return True
            
            response = self.client.indices.create(
                index=self.index_name,
                body=index_body
            )
            
            logger.info(f"Created index {self.index_name}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False
    
    def extract_cuisine_from_categories(self, categories: List[str]) -> str:
        cuisine_mapping = {
            'italian': 'Italian',
            'chinese': 'Chinese',
            'japanese': 'Japanese',
            'mexican': 'Mexican',
            'indian': 'Indian',
            'american': 'American',
            'french': 'French',
            'thai': 'Thai',
            'korean': 'Korean',
            'mediterranean': 'Mediterranean',
            'greek': 'Greek',
            'spanish': 'Spanish',
            'vietnamese': 'Vietnamese',
            'turkish': 'Turkish'
        }
        
        for category in categories:
            category_lower = category.lower()
            for key, value in cuisine_mapping.items():
                if key in category_lower:
                    return value
        
        return 'Other'
    
    def prepare_document(self, restaurant: Dict[str, Any]) -> Dict[str, Any]:
        categories = restaurant.get('categories', [])
        cuisine = self.extract_cuisine_from_categories(categories)
        
        return {
            'RestaurantID': restaurant.get('business_id', ''),
            'Cuisine': cuisine
        }
    
    def bulk_index_restaurants(self, restaurants: List[Dict[str, Any]], batch_size: int = 100):
        total_restaurants = len(restaurants)
        successful_indexes = 0
        failed_indexes = 0
        
        logger.info(f"Starting bulk indexing of {total_restaurants} restaurants")
        
        for i in range(0, total_restaurants, batch_size):
            batch = restaurants[i:i + batch_size]
            
            bulk_body = []
            for restaurant in batch:
                if not restaurant.get('business_id'):
                    logger.warning(f"Skipping restaurant without business_id: {restaurant}")
                    continue
                
                doc = self.prepare_document(restaurant)
                
                bulk_body.extend([
                    {
                        'index': {
                            '_index': self.index_name,
                            '_id': doc['RestaurantID']
                        }
                    },
                    doc
                ])
            
            if not bulk_body:
                logger.warning(f"No valid documents in batch {i//batch_size + 1}")
                continue
            
            try:
                response = self.client.bulk(body=bulk_body)
                
                batch_success = 0
                batch_failed = 0
                
                for item in response['items']:
                    if 'index' in item:
                        if item['index'].get('status') in [200, 201]:
                            batch_success += 1
                        else:
                            batch_failed += 1
                            logger.error(f"Failed to index document: {item['index']}")
                
                successful_indexes += batch_success
                failed_indexes += batch_failed
                
                logger.info(f"Batch {i//batch_size + 1}/{(total_restaurants-1)//batch_size + 1}: "
                           f"{batch_success} success, {batch_failed} failed")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in bulk indexing batch {i//batch_size + 1}: {e}")
                failed_indexes += len(batch) // 2
        
        logger.info(f"Bulk indexing completed. Success: {successful_indexes}, Failed: {failed_indexes}")
        return successful_indexes, failed_indexes
    
    def search_restaurants_by_cuisine(self, cuisine: str, size: int = 10) -> List[Dict[str, Any]]:
        query = {
            'query': {
                'term': {
                    'Cuisine': cuisine
                }
            },
            'size': size
        }
        
        try:
            response = self.client.search(
                index=self.index_name,
                body=query
            )
            
            hits = response['hits']['hits']
            restaurants = [hit['_source'] for hit in hits]
            
            logger.info(f"Found {len(restaurants)} {cuisine} restaurants")
            return restaurants
            
        except Exception as e:
            logger.error(f"Error searching for {cuisine} restaurants: {e}")
            return []
    
    def get_random_restaurants_by_cuisine(self, cuisine: str, size: int = 5) -> List[str]:
        query = {
            'query': {
                'function_score': {
                    'query': {
                        'term': {
                            'Cuisine': cuisine
                        }
                    },
                    'random_score': {}
                }
            },
            'size': size
        }
        
        try:
            response = self.client.search(
                index=self.index_name,
                body=query
            )
            
            hits = response['hits']['hits']
            restaurant_ids = [hit['_source']['RestaurantID'] for hit in hits]
            
            logger.info(f"Retrieved {len(restaurant_ids)} random {cuisine} restaurant IDs")
            return restaurant_ids
            
        except Exception as e:
            logger.error(f"Error getting random {cuisine} restaurants: {e}")
            return []
    
    def get_index_stats(self):
        try:
            stats = self.client.indices.stats(index=self.index_name)
            doc_count = stats['indices'][self.index_name]['total']['docs']['count']
            index_size = stats['indices'][self.index_name]['total']['store']['size_in_bytes']
            
            logger.info(f"Index {self.index_name} stats:")
            logger.info(f"  Document count: {doc_count}")
            logger.info(f"  Index size: {index_size} bytes")
            
            return {
                'doc_count': doc_count,
                'index_size': index_size
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return None
    
    def get_cuisine_distribution(self):
        query = {
            'size': 0,
            'aggs': {
                'cuisines': {
                    'terms': {
                        'field': 'Cuisine',
                        'size': 20
                    }
                }
            }
        }
        
        try:
            response = self.client.search(
                index=self.index_name,
                body=query
            )
            
            buckets = response['aggregations']['cuisines']['buckets']
            distribution = {bucket['key']: bucket['doc_count'] for bucket in buckets}
            
            logger.info("Cuisine distribution:")
            for cuisine, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {cuisine}: {count}")
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting cuisine distribution: {e}")
            return {}

def load_restaurants_from_file(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            restaurants = json.load(f)
        
        logger.info(f"Loaded {len(restaurants)} restaurants from {file_path}")
        return restaurants
        
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        return []

def main():
    endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    if not endpoint:
        logger.error("OPENSEARCH_ENDPOINT environment variable not set")
        return
    
    index_name = os.environ.get('OPENSEARCH_INDEX', 'restaurants')
    
    loader = OpenSearchLoader(endpoint, index_name=index_name)
    
    if not loader.create_index():
        logger.error("Failed to create index")
        return
    
    data_file = 'data/restaurants.json'
    restaurants = load_restaurants_from_file(data_file)
    
    if not restaurants:
        logger.error("No restaurant data to load")
        return
    
    success_count, fail_count = loader.bulk_index_restaurants(restaurants)
    
    if success_count > 0:
        logger.info("Waiting for indexing to complete...")
        time.sleep(2)
        
        loader.get_index_stats()
        loader.get_cuisine_distribution()
        
        logger.info("Testing search functionality...")
        italian_restaurants = loader.get_random_restaurants_by_cuisine('Italian', 3)
        logger.info(f"Sample Italian restaurant IDs: {italian_restaurants}")
    
    logger.info(f"OpenSearch loading completed. {success_count} successful, {fail_count} failed")

if __name__ == "__main__":
    main()
