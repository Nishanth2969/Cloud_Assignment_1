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
    # Get Lambda request ID for tracking
    request_id = context.request_id if context else 'unknown'
    
    logger.info(f"[RequestId: {request_id}] Received event: {json.dumps(event)}")

    try:
        queue_url = os.environ.get('SQS_QUEUE_URL')
        if not queue_url:
            logger.error(f"[RequestId: {request_id}] SQS_QUEUE_URL environment variable not set")
            return {'statusCode': 500, 'body': 'Configuration error'}

        messages = receive_messages_from_sqs(queue_url, request_id)

        if not messages:
            logger.info(f"[RequestId: {request_id}] No messages to process")
            return {'statusCode': 200, 'body': 'No messages processed'}

        processed_count = 0
        failed_count = 0

        for message in messages:
            message_id = message.get('MessageId', 'unknown')
            try:
                # Process the message - only delete if successful
                if process_dining_request(message, request_id):
                    delete_message_from_sqs(queue_url, message['ReceiptHandle'], message_id, request_id)
                    processed_count += 1
                    logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Successfully processed and deleted")
                else:
                    # Message processing failed - do NOT delete, let it retry
                    failed_count += 1
                    logger.warning(f"[RequestId: {request_id}] [MessageId: {message_id}] Processing failed - message NOT deleted, will be retried")
            except Exception as e:
                # Exception during processing - do NOT delete, let it retry
                failed_count += 1
                logger.error(
                    f"[RequestId: {request_id}] [MessageId: {message_id}] "
                    f"Exception during processing: {str(e)} - message NOT deleted, will be retried or moved to DLQ"
                )
                # Do NOT delete the message - SQS will retry or move to DLQ after maxReceiveCount

        logger.info(f"[RequestId: {request_id}] Processed {processed_count} messages successfully, {failed_count} failed")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'requestId': request_id,
                'processed': processed_count,
                'failed': failed_count
            })
        }

    except Exception as e:
        logger.error(f"[RequestId: {request_id}] Error in lambda handler: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}


def receive_messages_from_sqs(queue_url: str, request_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
    try:
        sqs = get_sqs_client()
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=1,
            MessageAttributeNames=['All'],
            AttributeNames=['All']  # Include ApproximateReceiveCount for DLQ tracking
        )

        messages = response.get('Messages', [])
        logger.info(f"[RequestId: {request_id}] Received {len(messages)} messages from SQS")
        
        # Log receive count for each message (for DLQ monitoring)
        for msg in messages:
            receive_count = msg.get('Attributes', {}).get('ApproximateReceiveCount', 'unknown')
            message_id = msg.get('MessageId', 'unknown')
            logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Receive count: {receive_count}")

        return messages

    except Exception as e:
        logger.error(f"[RequestId: {request_id}] Error receiving messages from SQS: {str(e)}")
        return []


def delete_message_from_sqs(queue_url: str, receipt_handle: str, message_id: str, request_id: str):
    try:
        sqs = get_sqs_client()
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Message successfully deleted from SQS")
    except Exception as e:
        logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Error deleting message from SQS: {str(e)}")


def process_dining_request(message: Dict[str, Any], request_id: str) -> bool:
    message_id = message.get('MessageId', 'unknown')
    
    try:
        body = json.loads(message['Body'])
        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Processing dining request: {body}")

        required_fields = ['location', 'cuisine', 'dining_time', 'party_size', 'email']
        for field in required_fields:
            if field not in body:
                logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Missing required field: {field}")
                return False

        restaurant_ids = get_restaurant_recommendations(body['cuisine'], request_id, message_id)

        if not restaurant_ids:
            logger.warning(f"[RequestId: {request_id}] [MessageId: {message_id}] No restaurants found for cuisine: {body['cuisine']}")
            # Still try to send "no results" email
            try:
                send_no_results_email(body, request_id, message_id)
                return True
            except Exception as email_error:
                logger.error(
                    f"[RequestId: {request_id}] [MessageId: {message_id}] "
                    f"Failed to send no-results email: {str(email_error)} - "
                    f"Error type: {type(email_error).__name__}"
                )
                return False  # Failed to send email, will retry

        restaurant_details = get_restaurant_details_from_dynamodb(restaurant_ids, request_id, message_id)

        if restaurant_details:
            # Critical: Email sending - if this fails, we must return False to retry
            try:
                send_recommendations_email(body, restaurant_details, request_id, message_id)
                logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Successfully sent recommendations email")
                return True
            except Exception as email_error:
                # Log detailed error for DLQ debugging
                logger.error(
                    f"[RequestId: {request_id}] [MessageId: {message_id}] "
                    f"FAILED to send recommendations email: {str(email_error)} - "
                    f"Error type: {type(email_error).__name__} - "
                    f"Recipient: {body.get('email', 'unknown')} - "
                    f"Message will be retried or moved to DLQ after maxReceiveCount"
                )
                return False  # Email failed, do not delete message
        else:
            logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Failed to get restaurant details from DynamoDB")
            return False

    except json.JSONDecodeError as e:
        logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Error parsing message body: {str(e)}")
        return False  # Invalid message format, will retry
    except Exception as e:
        logger.error(
            f"[RequestId: {request_id}] [MessageId: {message_id}] "
            f"Unexpected error processing dining request: {str(e)} - "
            f"Error type: {type(e).__name__}"
        )
        import traceback
        logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Traceback: {traceback.format_exc()}")
        return False  # Unexpected error, will retry


def get_restaurant_recommendations(cuisine: str, request_id: str, message_id: str, count: int = 5) -> List[str]:
    try:
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        if not opensearch_endpoint:
            logger.warning(f"[RequestId: {request_id}] [MessageId: {message_id}] OPENSEARCH_ENDPOINT not set, using fallback method")
            return get_random_restaurants_from_dynamodb(cuisine, count, request_id, message_id)

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

        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Retrieved {len(restaurant_ids)} restaurant IDs for {cuisine}")
        return restaurant_ids

    except Exception as e:
        logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Error querying OpenSearch: {str(e)}")
        return get_random_restaurants_from_dynamodb(cuisine, count, request_id, message_id)


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


def get_random_restaurants_from_dynamodb(cuisine: str, count: int, request_id: str, message_id: str) -> List[str]:
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

        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Retrieved {len(restaurant_ids)} restaurant IDs from DynamoDB fallback")
        return restaurant_ids

    except Exception as e:
        logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Error getting restaurants from DynamoDB: {str(e)}")
        return []


def get_restaurant_details_from_dynamodb(restaurant_ids: List[str], request_id: str, message_id: str) -> List[Dict[str, Any]]:
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
                logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Error getting restaurant {restaurant_id}: {str(e)}")
                continue

        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Retrieved details for {len(restaurants)} restaurants")
        return restaurants

    except Exception as e:
        logger.error(f"[RequestId: {request_id}] [MessageId: {message_id}] Error getting restaurant details: {str(e)}")
        return []


def send_recommendations_email(request_data: Dict[str, Any], restaurants: List[Dict[str, Any]], request_id: str, message_id: str):
    try:
        ses = get_ses_client()
        sender_email = os.environ.get('SES_SENDER_EMAIL', 'noreply@diningconcierge.com')
        recipient_email = request_data['email']

        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Attempting to send email to: {recipient_email}")

        subject = f"Restaurant Recommendations for {request_data['cuisine']} Cuisine"

        html_body = format_recommendations_email_html(request_data, restaurants)
        text_body = format_recommendations_email_text(request_data, restaurants)

        response = ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [recipient_email]
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

        ses_message_id = response['MessageId']
        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Email sent successfully to {recipient_email} - SES MessageId: {ses_message_id}")

    except Exception as e:
        # Log detailed error information for DLQ debugging
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(
            f"[RequestId: {request_id}] [MessageId: {message_id}] "
            f"SES send_email FAILED - "
            f"Error Type: {error_type} - "
            f"Error Message: {error_message} - "
            f"Recipient: {request_data.get('email', 'unknown')} - "
            f"Sender: {sender_email}"
        )
        # Re-raise to trigger retry/DLQ mechanism
        raise


def send_no_results_email(request_data: Dict[str, Any], request_id: str, message_id: str):
    try:
        ses = get_ses_client()
        sender_email = os.environ.get('SES_SENDER_EMAIL', 'noreply@diningconcierge.com')
        recipient_email = request_data['email']

        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] Attempting to send no-results email to: {recipient_email}")

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

        response = ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [recipient_email]
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

        ses_message_id = response['MessageId']
        logger.info(f"[RequestId: {request_id}] [MessageId: {message_id}] No-results email sent to {recipient_email} - SES MessageId: {ses_message_id}")

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        logger.error(
            f"[RequestId: {request_id}] [MessageId: {message_id}] "
            f"Error sending no-results email - "
            f"Error Type: {error_type} - "
            f"Error Message: {error_message} - "
            f"Recipient: {recipient_email}"
        )
        # Re-raise to trigger retry/DLQ mechanism
        raise


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
