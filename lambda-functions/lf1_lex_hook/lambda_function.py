import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        invocation_source = event.get('invocationSource')
        intent_name = event['sessionState']['intent']['name']
        slots = event['sessionState']['intent']['slots']
        session_attributes = event['sessionState'].get('sessionAttributes', {})

        # Handle DiningSuggestionsIntent
        if intent_name == 'DiningSuggestionsIntent':
            # Use originalValue instead of interpretedValue for Cuisine
            cuisine_slot = slots.get('Cuisine')
            if cuisine_slot and 'value' in cuisine_slot:
                cuisine = cuisine_slot['value'].get('originalValue', cuisine_slot['value'].get('interpretedValue'))
            else:
                cuisine = None
            dining_time = get_slot_value(slots, 'DiningTime')
            party_size = get_slot_value(slots, 'PartySize')
            email = get_slot_value(slots, 'Email')

            # If all slots filled, send to SQS and fulfill
            if cuisine and dining_time and party_size and email:
                try:
                    queue_url = 'https://sqs.us-east-1.amazonaws.com/141507053403/q-dining-suggestions'
                    sqs = boto3.client('sqs', region_name='us-east-1')

                    response = sqs.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps({
                            'location': 'Manhattan',
                            'cuisine': cuisine,
                            'dining_time': dining_time,
                            'party_size': party_size,
                            'email': email,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    )

                    logger.info(f"Message sent: {response['MessageId']}")
                    return close(session_attributes, 'DiningSuggestionsIntent', 'Fulfilled',
                                 "You're all set. Expect my suggestions shortly! Have a good day.")

                except Exception as e:
                    logger.error(f"Error: {str(e)}")
                    return close(session_attributes, 'DiningSuggestionsIntent', 'Failed',
                                 "Sorry, I'm having trouble.")

            # If not all slots filled, delegate back to Lex
            return {
                'sessionState': {
                    'sessionAttributes': session_attributes,
                    'dialogAction': {'type': 'Delegate'},
                    'intent': {'name': intent_name, 'slots': slots}
                }
            }

        # Other intents...
        elif intent_name == 'GreetingIntent':
            return close(session_attributes, 'GreetingIntent', 'Fulfilled',
                         "Hi there, how can I help?")

        elif intent_name == 'ThankYouIntent':
            return close(session_attributes, 'ThankYouIntent', 'Fulfilled',
                         "You're welcome!")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return close({}, 'FallbackIntent', 'Failed', "Sorry, I'm having trouble.")


def get_slot_value(slots, slot_name):
    if slot_name in slots and slots[slot_name] is not None:
        if 'value' in slots[slot_name]:
            return slots[slot_name]['value']['interpretedValue']
    return None


def close(session_attributes, intent_name, fulfillment_state, message):
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {'type': 'Close'},
            'intent': {'name': intent_name, 'state': fulfillment_state}
        },
        'messages': [{'contentType': 'PlainText', 'content': message}]
    }