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
            # Collect all 5 required slots
            location = get_slot_value(slots, 'Location')
            
            # Use originalValue instead of interpretedValue for Cuisine
            cuisine_slot = slots.get('Cuisine')
            if cuisine_slot and 'value' in cuisine_slot:
                cuisine = cuisine_slot['value'].get('originalValue', cuisine_slot['value'].get('interpretedValue'))
            else:
                cuisine = None
            
            dining_time = get_slot_value(slots, 'DiningTime')
            party_size = get_slot_value(slots, 'PartySize')
            email = get_slot_value(slots, 'Email')

            # If all 5 slots filled, send to SQS and fulfill
            if location and cuisine and dining_time and party_size and email:
                try:
                    queue_url = 'https://sqs.us-east-1.amazonaws.com/141507053403/q-dining-suggestions'
                    sqs = boto3.client('sqs', region_name='us-east-1')

                    response = sqs.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps({
                            'location': location,
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
                         "Hi there! I'm your dining concierge. I can help you find amazing restaurants in Manhattan. "
                         "Just tell me what cuisine you're craving, and I'll send you personalized recommendations!")

        elif intent_name == 'ThankYouIntent':
            return close(session_attributes, 'ThankYouIntent', 'Fulfilled',
                         "You're very welcome! Enjoy your dining experience! Feel free to come back anytime for more recommendations.")

        elif intent_name == 'HelpIntent':
            return close(session_attributes, 'HelpIntent', 'Fulfilled',
                         "I can help you find the perfect restaurant! Just tell me: "
                         "1) What type of cuisine you want (like Italian, Chinese, Thai, etc.) "
                         "2) When you're planning to dine "
                         "3) How many people will be dining "
                         "4) Your email address to receive recommendations. "
                         "You can start by saying something like 'I want Italian food' or 'Find me a restaurant'")

        elif intent_name == 'CancelIntent':
            return close(session_attributes, 'CancelIntent', 'Fulfilled',
                         "No problem! Your request has been cancelled. Come back anytime you're hungry!")

        elif intent_name == 'ChangeMindIntent':
            # Clear session attributes to start fresh
            return close({}, 'ChangeMindIntent', 'Fulfilled',
                         "Sure thing! Let's start over. What type of cuisine are you in the mood for?")

        elif intent_name == 'RestaurantTypesIntent':
            return close(session_attributes, 'RestaurantTypesIntent', 'Fulfilled',
                         "I can help you find restaurants for many cuisines including: "
                         "Italian, Chinese, Thai, Indian, French, Japanese, Mexican, American, Mediterranean, and more! "
                         "What sounds good to you?")

        elif intent_name == 'LocationIntent':
            return close(session_attributes, 'LocationIntent', 'Fulfilled',
                         "I specialize in Manhattan restaurants! From the Upper East Side to Downtown, "
                         "I know all the best spots. What type of cuisine are you looking for?")

        elif intent_name == 'FeedbackIntent':
            return close(session_attributes, 'FeedbackIntent', 'Fulfilled',
                         "Thank you for your feedback! We're always working to improve. "
                         "Is there anything else I can help you with today?")
        
        else:
            # Handle unknown intents
            logger.warning(f"Unknown intent: {intent_name}")
            return close(session_attributes, intent_name, 'Fulfilled',
                         "I'm sorry, I didn't quite understand that. Could you try rephrasing? "
                         "Or say 'help' to learn what I can do.")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return close({}, 'FallbackIntent', 'Failed', 
                     "I'm sorry, I didn't quite understand that. Could you try rephrasing? "
                     "Or say 'help' to learn what I can do.")


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