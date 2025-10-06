import json
import boto3
import os
import logging
from typing import List, Dict, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import random
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_sqs_client():
    return boto3.client('sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


def get_dynamodb_resource():
    return boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


def get_ses_client():
    return boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        queue_url = os.environ.get('SQS_QUEUE_URL')
        if not queue_url:
            logger.error("SQS_QUEUE_URL environment variable not set")
            return {'statusCode': 500, 'body': 'Configuration error'}

        messages = receive_messages_from_sqs(queue_url)

        if not messages:
            logger.info("No messages to process")
            return {'statusCode': 200, 'body': 'No messages processed'}

        processed_count = 0
        failed_count = 0

        for message in messages:
            try:
                if process_dining_request(message):
                    delete_message_from_sqs(queue_url, message['ReceiptHandle'])
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Error processing message {message.get('MessageId', 'unknown')}: {str(e)}")
                failed_count += 1

        logger.info(f"Processed {processed_count} messages successfully, {failed_count} failed")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': processed_count,
                'failed': failed_count
            })
        }

    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}


def receive_messages_from_sqs(queue_url: str, max_messages: int = 10) -> List[Dict[str, Any]]:
    try:
        sqs = get_sqs_client()
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=1,
            MessageAttributeNames=['All']
        )

        messages = response.get('Messages', [])
        logger.info(f"Received {len(messages)} messages from SQS")

        return messages

    except Exception as e:
        logger.error(f"Error receiving messages from SQS: {str(e)}")
        return []


def delete_message_from_sqs(queue_url: str, receipt_handle: str):
    try:
        sqs = get_sqs_client()
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.info("Message deleted from SQS")
    except Exception as e:
        logger.error(f"Error deleting message from SQS: {str(e)}")


def process_dining_request(message: Dict[str, Any]) -> bool:
    try:
        body = json.loads(message['Body'])
        logger.info(f"Processing dining request: {body}")

        required_fields = ['location', 'cuisine', 'dining_time', 'party_size', 'email']
        for field in required_fields:
            if field not in body:
                logger.error(f"Missing required field: {field}")
                return False

        restaurant_ids = get_restaurant_recommendations(body['cuisine'])

        if not restaurant_ids:
            logger.warning(f"No restaurants found for cuisine: {body['cuisine']}")
            send_no_results_email(body)
            return True

        restaurant_details = get_restaurant_details_from_dynamodb(restaurant_ids)

        if restaurant_details:
            send_recommendations_email(body, restaurant_details)
            return True
        else:
            logger.error("Failed to get restaurant details from DynamoDB")
            return False

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing message body: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error processing dining request: {str(e)}")
        return False


def get_restaurant_recommendations(cuisine: str, count: int = 5) -> List[str]:
    try:
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        if not opensearch_endpoint:
            logger.warning("OPENSEARCH_ENDPOINT not set, using fallback method")
            return get_random_restaurants_from_dynamodb(cuisine, count)

        opensearch_client = get_opensearch_client(opensearch_endpoint)

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
            'size': count
        }

        index_name = os.environ.get('OPENSEARCH_INDEX', 'restaurants')
        response = opensearch_client.search(
            index=index_name,
            body=query
        )

        hits = response['hits']['hits']
        restaurant_ids = [hit['_source']['RestaurantID'] for hit in hits]

        logger.info(f"Retrieved {len(restaurant_ids)} restaurant IDs for {cuisine}")
        return restaurant_ids

    except Exception as e:
        logger.error(f"Error querying OpenSearch: {str(e)}")
        return get_random_restaurants_from_dynamodb(cuisine, count)


def get_opensearch_client(endpoint: str):
    region = os.environ.get('AWS_REGION', 'us-east-1')

    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'es',
        session_token=credentials.token
    )

    return OpenSearch(
        hosts=[{'host': endpoint.replace('https://', '').replace('http://', ''), 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )


def get_random_restaurants_from_dynamodb(cuisine: str, count: int = 5) -> List[str]:
    try:
        dynamodb = get_dynamodb_resource()
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'yelp-restaurants')
        table = dynamodb.Table(table_name)

        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('categories').contains(cuisine),
            ProjectionExpression='business_id'
        )

        items = response.get('Items', [])
        restaurant_ids = [item['business_id'] for item in items if 'business_id' in item]

        if len(restaurant_ids) > count:
            restaurant_ids = random.sample(restaurant_ids, count)

        logger.info(f"Retrieved {len(restaurant_ids)} restaurant IDs from DynamoDB fallback")
        return restaurant_ids

    except Exception as e:
        logger.error(f"Error getting restaurants from DynamoDB: {str(e)}")
        return []


def get_restaurant_details_from_dynamodb(restaurant_ids: List[str]) -> List[Dict[str, Any]]:
    try:
        dynamodb = get_dynamodb_resource()
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'yelp-restaurants')
        table = dynamodb.Table(table_name)

        restaurants = []

        for restaurant_id in restaurant_ids:
            try:
                response = table.get_item(
                    Key={'business_id': restaurant_id}
                )

                if 'Item' in response:
                    item = response['Item']
                    restaurant = {
                        'name': item.get('name', 'Unknown Restaurant'),
                        'address': item.get('address', 'Address not available'),
                        'rating': float(item.get('rating', 0)),
                        'review_count': int(item.get('review_count', 0)),
                        'phone': item.get('phone', ''),
                        'url': item.get('url', ''),
                        'price': item.get('price', ''),
                        'categories': item.get('categories', [])
                    }
                    restaurants.append(restaurant)

            except Exception as e:
                logger.error(f"Error getting restaurant {restaurant_id}: {str(e)}")
                continue

        logger.info(f"Retrieved details for {len(restaurants)} restaurants")
        return restaurants

    except Exception as e:
        logger.error(f"Error getting restaurant details: {str(e)}")
        return []


def send_recommendations_email(request_data: Dict[str, Any], restaurants: List[Dict[str, Any]]):
    try:
        ses = get_ses_client()
        sender_email = os.environ.get('SES_SENDER_EMAIL', 'noreply@diningconcierge.com')

        subject = f"Restaurant Recommendations for {request_data['cuisine']} Cuisine"

        html_body = format_recommendations_email_html(request_data, restaurants)
        text_body = format_recommendations_email_text(request_data, restaurants)

        response = ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [request_data['email']]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    },
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        logger.info(f"Email sent successfully to {request_data['email']}: {response['MessageId']}")

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise


def send_no_results_email(request_data: Dict[str, Any]):
    try:
        ses = get_ses_client()
        sender_email = os.environ.get('SES_SENDER_EMAIL', 'noreply@diningconcierge.com')

        subject = f"No {request_data['cuisine']} Restaurants Found"

        body = f"""
Dear Diner,

We apologize, but we couldn't find any {request_data['cuisine']} restaurants matching your criteria in {request_data['location']}.

Please try:
- A different cuisine type
- A broader location search
- Contacting us directly for personalized assistance

Thank you for using our Dining Concierge service!

Best regards,
The Dining Concierge Team
        """

        ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [request_data['email']]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        logger.info(f"No results email sent to {request_data['email']}")

    except Exception as e:
        logger.error(f"Error sending no results email: {str(e)}")


def format_recommendations_email_html(request_data: Dict[str, Any], restaurants: List[Dict[str, Any]]) -> str:
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #d4af37; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .restaurant {{ border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }}
            .restaurant-name {{ font-size: 18px; font-weight: bold; color: #d4af37; }}
            .rating {{ color: #ff6b35; font-weight: bold; }}
            .footer {{ background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Your {request_data['cuisine']} Restaurant Recommendations</h1>
        </div>

        <div class="content">
            <p>Hello!</p>

            <p>Based on your request for <strong>{request_data['cuisine']}</strong> restaurants in <strong>{request_data['location']}</strong> 
            for <strong>{request_data['party_size']}</strong> people at <strong>{request_data['dining_time']}</strong>, 
            here are our top recommendations:</p>
    """

    for i, restaurant in enumerate(restaurants, 1):
        rating_stars = "★" * int(restaurant['rating']) + "☆" * (5 - int(restaurant['rating']))

        html += f"""
            <div class="restaurant">
                <div class="restaurant-name">{i}. {restaurant['name']}</div>
                <p><strong>Address:</strong> {restaurant['address']}</p>
                <p><strong>Rating:</strong> <span class="rating">{restaurant['rating']}/5 {rating_stars}</span> ({restaurant['review_count']} reviews)</p>
        """

        if restaurant.get('phone'):
            html += f"<p><strong>Phone:</strong> {restaurant['phone']}</p>"

        if restaurant.get('price'):
            html += f"<p><strong>Price Range:</strong> {restaurant['price']}</p>"

        if restaurant.get('url'):
            html += f'<p><a href="{restaurant["url"]}" target="_blank">View on Yelp</a></p>'

        html += "</div>"

    html += """
        <p>We hope you enjoy your dining experience! Feel free to ask for more recommendations anytime.</p>

        <p>Best regards,<br>
        The Dining Concierge Team</p>
        </div>

        <div class="footer">
            <p>This email was sent by the Dining Concierge service. 
            If you have any questions, please contact our support team.</p>
        </div>
    </body>
    </html>
    """

    return html


def format_recommendations_email_text(request_data: Dict[str, Any], restaurants: List[Dict[str, Any]]) -> str:
    text = f"""
Your {request_data['cuisine']} Restaurant Recommendations

Hello!

Based on your request for {request_data['cuisine']} restaurants in {request_data['location']} 
for {request_data['party_size']} people at {request_data['dining_time']}, 
here are our top recommendations:

"""

    for i, restaurant in enumerate(restaurants, 1):
        text += f"""
{i}. {restaurant['name']}
   Address: {restaurant['address']}
   Rating: {restaurant['rating']}/5 ({restaurant['review_count']} reviews)
"""

        if restaurant.get('phone'):
            text += f"   Phone: {restaurant['phone']}\n"

        if restaurant.get('price'):
            text += f"   Price Range: {restaurant['price']}\n"

        if restaurant.get('url'):
            text += f"   Yelp URL: {restaurant['url']}\n"

        text += "\n"

    text += """
We hope you enjoy your dining experience! Feel free to ask for more recommendations anytime.

Best regards,
The Dining Concierge Team

---
This email was sent by the Dining Concierge service.
"""

    return text
