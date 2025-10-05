import json
import boto3
import os
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_sqs_client():
    return boto3.client('sqs', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        intent_name = event['currentIntent']['name']
        slots = event['currentIntent']['slots']
        session_attributes = event.get('sessionAttributes', {})
        
        if intent_name == 'GreetingIntent':
            return handle_greeting_intent(event)
        elif intent_name == 'ThankYouIntent':
            return handle_thank_you_intent(event)
        elif intent_name == 'DiningSuggestionsIntent':
            return handle_dining_suggestions_intent(event, slots, session_attributes)
        else:
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': "I'm sorry, I didn't understand that. I can help you find restaurants in Manhattan. What type of cuisine are you looking for?"
                }
            )
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return close(
            {},
            'Failed',
            {
                'contentType': 'PlainText',
                'content': "I'm sorry, I'm having trouble right now. Please try again in a moment."
            }
        )

def handle_greeting_intent(event):
    session_attributes = event.get('sessionAttributes', {})
    
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': "Hello! I'm your dining concierge. I can help you find great restaurants in Manhattan. What type of cuisine are you in the mood for today?"
        }
    )

def handle_thank_you_intent(event):
    session_attributes = event.get('sessionAttributes', {})
    
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': "You're welcome! I hope you have a wonderful dining experience. Feel free to ask me anytime for more restaurant recommendations!"
        }
    )

def handle_dining_suggestions_intent(event, slots, session_attributes):
    location = get_slot_value(slots, 'Location')
    cuisine = get_slot_value(slots, 'Cuisine')
    dining_time = get_slot_value(slots, 'DiningTime')
    party_size = get_slot_value(slots, 'PartySize')
    email = get_slot_value(slots, 'Email')
    
    validation_result = validate_slots(location, cuisine, dining_time, party_size, email)
    
    if not validation_result['isValid']:
        return elicit_slot(
            session_attributes,
            event['currentIntent']['name'],
            slots,
            validation_result['violatedSlot'],
            {
                'contentType': 'PlainText',
                'content': validation_result['message']
            }
        )
    
    if all([location, cuisine, dining_time, party_size, email]):
        try:
            send_to_sqs({
                'location': location,
                'cuisine': cuisine,
                'dining_time': dining_time,
                'party_size': party_size,
                'email': email,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return close(
                session_attributes,
                'Fulfilled',
                {
                    'contentType': 'PlainText',
                    'content': f"Perfect! I'm searching for {cuisine} restaurants in {location} for {party_size} people at {dining_time}. I'll send you some great recommendations via email at {email} shortly!"
                }
            )
        
        except Exception as e:
            logger.error(f"Error sending to SQS: {str(e)}")
            return close(
                session_attributes,
                'Failed',
                {
                    'contentType': 'PlainText',
                    'content': "I'm sorry, I'm having trouble processing your request right now. Please try again in a moment."
                }
            )
    
    return delegate(session_attributes, slots)

def validate_slots(location, cuisine, dining_time, party_size, email):
    if location and not validate_location(location):
        return {
            'isValid': False,
            'violatedSlot': 'Location',
            'message': 'I can only help you find restaurants in Manhattan. Could you please specify a location in Manhattan?'
        }
    
    if cuisine and not validate_cuisine(cuisine):
        return {
            'isValid': False,
            'violatedSlot': 'Cuisine',
            'message': 'I can help you find restaurants for many cuisines like Italian, Chinese, Japanese, Mexican, Indian, and more. What type of cuisine would you like?'
        }
    
    if dining_time and not validate_dining_time(dining_time):
        return {
            'isValid': False,
            'violatedSlot': 'DiningTime',
            'message': 'Please provide a valid time for your dining reservation (e.g., "7:00 PM" or "tomorrow at 6 PM").'
        }
    
    if party_size and not validate_party_size(party_size):
        return {
            'isValid': False,
            'violatedSlot': 'PartySize',
            'message': 'Party size should be between 1 and 20 people. How many people will be dining?'
        }
    
    if email and not validate_email(email):
        return {
            'isValid': False,
            'violatedSlot': 'Email',
            'message': 'Please provide a valid email address so I can send you the restaurant recommendations.'
        }
    
    return {'isValid': True}

def validate_location(location):
    manhattan_keywords = ['manhattan', 'nyc', 'new york city', 'midtown', 'downtown', 'upper east side', 
                         'upper west side', 'soho', 'tribeca', 'chelsea', 'village', 'times square']
    return any(keyword in location.lower() for keyword in manhattan_keywords)

def validate_cuisine(cuisine):
    valid_cuisines = ['italian', 'chinese', 'japanese', 'mexican', 'indian', 'american', 'french', 
                     'thai', 'korean', 'mediterranean', 'greek', 'spanish', 'vietnamese', 'turkish']
    return cuisine.lower() in valid_cuisines

def validate_dining_time(dining_time):
    try:
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(am|pm)',
            r'\d{1,2}\s*(am|pm)',
            r'(today|tomorrow|tonight)',
            r'\d{4}-\d{2}-\d{2}'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, dining_time.lower()):
                return True
        
        return False
    except:
        return False

def validate_party_size(party_size):
    try:
        size = int(party_size)
        return 1 <= size <= 20
    except:
        return False

def validate_email(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def send_to_sqs(message_data):
    queue_url = os.environ.get('SQS_QUEUE_URL')
    if not queue_url:
        raise Exception("SQS_QUEUE_URL environment variable not set")
    
    sqs = get_sqs_client()
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_data),
        MessageAttributes={
            'RequestType': {
                'StringValue': 'DiningRequest',
                'DataType': 'String'
            }
        }
    )
    
    logger.info(f"Message sent to SQS: {response['MessageId']}")
    return response

def get_slot_value(slots, slot_name):
    if slot_name in slots and slots[slot_name]:
        return slots[slot_name]
    return None

def close(session_attributes, fulfillment_state, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }
