import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


def lambda_handler(event, context):
    print("Starting data load...")

    # DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('yelp-restaurants')

    # OpenSearch
    region = 'us-east-1'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'es',
        session_token=credentials.token
    )

    opensearch = OpenSearch(
        hosts=[{
            'host': 'search-restaurants-lqyixzg7pmf2yhqgk3ds7lguqa.us-east-1.es.amazonaws.com',
            'port': 443
        }],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    # Scan DynamoDB
    print("Reading from DynamoDB...")
    response = table.scan()
    items = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])

    print(f"Found {len(items)} restaurants")

    # Load into OpenSearch
    loaded = 0
    for item in items:
        try:
            # Handle DynamoDB List format: [{"S": "Chinese"}, {"S": "Ramen"}]
            categories = item.get('categories', [])

            if categories and len(categories) > 0:
                # Extract first category
                first_cat = categories[0]
                if isinstance(first_cat, dict) and 'S' in first_cat:
                    cuisine = first_cat['S']
                elif isinstance(first_cat, str):
                    cuisine = first_cat
                else:
                    cuisine = str(first_cat)
            else:
                cuisine = 'Unknown'

            business_id = item.get('business_id')

            print(f"Loading: {business_id} - {cuisine}")

            opensearch.index(
                index='restaurants',
                body={
                    'RestaurantID': business_id,
                    'Cuisine': cuisine
                },
                id=business_id
            )
            loaded += 1

            if loaded % 10 == 0:
                print(f"Loaded {loaded}...")

        except Exception as e:
            print(f"Error loading {item.get('business_id', 'unknown')}: {e}")

    print(f"✅ DONE! Loaded {loaded} restaurants")
    return {'statusCode': 200, 'body': f'Loaded {loaded} restaurants'}