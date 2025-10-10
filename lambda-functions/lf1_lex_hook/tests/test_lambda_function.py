import pytest
import json
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.append('..')

from lambda_function import (
    lambda_handler, 
    validate_slots, 
    validate_location, 
    validate_cuisine, 
    validate_dining_time, 
    validate_party_size, 
    validate_email
)

class TestValidators:
    
    def test_validate_location_valid(self):
        assert validate_location("Manhattan") == True
        assert validate_location("Upper East Side, Manhattan") == True
        assert validate_location("NYC") == True
        assert validate_location("Midtown Manhattan") == True
    
    def test_validate_location_invalid(self):
        assert validate_location("Brooklyn") == False
        assert validate_location("Queens") == False
        assert validate_location("Los Angeles") == False
    
    def test_validate_cuisine_valid(self):
        assert validate_cuisine("Italian") == True
        assert validate_cuisine("chinese") == True
        assert validate_cuisine("JAPANESE") == True
    
    def test_validate_cuisine_invalid(self):
        assert validate_cuisine("Martian") == False
        assert validate_cuisine("") == False
    
    def test_validate_dining_time_valid(self):
        assert validate_dining_time("7:00 PM") == True
        assert validate_dining_time("12:30 am") == True
        assert validate_dining_time("today") == True
        assert validate_dining_time("tomorrow") == True
        assert validate_dining_time("2023-12-25") == True
    
    def test_validate_dining_time_invalid(self):
        assert validate_dining_time("invalid time") == False
        assert validate_dining_time("25:00") == False
    
    def test_validate_party_size_valid(self):
        assert validate_party_size("1") == True
        assert validate_party_size("10") == True
        assert validate_party_size("20") == True
    
    def test_validate_party_size_invalid(self):
        assert validate_party_size("0") == False
        assert validate_party_size("21") == False
        assert validate_party_size("abc") == False
    
    def test_validate_email_valid(self):
        assert validate_email("test@example.com") == True
        assert validate_email("user.name+tag@domain.co.uk") == True
    
    def test_validate_email_invalid(self):
        assert validate_email("invalid-email") == False
        assert validate_email("@domain.com") == False
        assert validate_email("user@") == False

class TestSlotValidation:
    
    def test_validate_slots_all_valid(self):
        result = validate_slots(
            "Manhattan", 
            "Italian", 
            "7:00 PM", 
            "4", 
            "test@example.com"
        )
        assert result['isValid'] == True
    
    def test_validate_slots_invalid_location(self):
        result = validate_slots(
            "Brooklyn", 
            "Italian", 
            "7:00 PM", 
            "4", 
            "test@example.com"
        )
        assert result['isValid'] == False
        assert result['violatedSlot'] == 'Location'
    
    def test_validate_slots_invalid_party_size(self):
        result = validate_slots(
            "Manhattan", 
            "Italian", 
            "7:00 PM", 
            "25", 
            "test@example.com"
        )
        assert result['isValid'] == False
        assert result['violatedSlot'] == 'PartySize'

class TestLambdaHandler:
    
    def test_greeting_intent(self):
        event = {
            'currentIntent': {
                'name': 'GreetingIntent',
                'slots': {}
            },
            'sessionAttributes': {}
        }
        
        result = lambda_handler(event, {})
        
        assert result['dialogAction']['type'] == 'Close'
        assert result['dialogAction']['fulfillmentState'] == 'Fulfilled'
        assert 'dining concierge' in result['dialogAction']['message']['content'].lower()
    
    def test_thank_you_intent(self):
        event = {
            'currentIntent': {
                'name': 'ThankYouIntent',
                'slots': {}
            },
            'sessionAttributes': {}
        }
        
        result = lambda_handler(event, {})
        
        assert result['dialogAction']['type'] == 'Close'
        assert result['dialogAction']['fulfillmentState'] == 'Fulfilled'
        assert 'welcome' in result['dialogAction']['message']['content'].lower()
    
    @patch.dict(os.environ, {'SQS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'})
    @patch('lambda_function.get_sqs_client')
    def test_dining_suggestions_intent_complete(self, mock_get_sqs_client):
        mock_sqs = MagicMock()
        mock_get_sqs_client.return_value = mock_sqs
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}
        
        event = {
            'currentIntent': {
                'name': 'DiningSuggestionsIntent',
                'slots': {
                    'Location': 'Manhattan',
                    'Cuisine': 'Italian',
                    'DiningTime': '7:00 PM',
                    'PartySize': '4',
                    'Email': 'test@example.com'
                }
            },
            'sessionAttributes': {}
        }
        
        result = lambda_handler(event, {})
        
        assert result['dialogAction']['type'] == 'Close'
        assert result['dialogAction']['fulfillmentState'] == 'Fulfilled'
        assert 'Italian restaurants' in result['dialogAction']['message']['content']
        mock_sqs.send_message.assert_called_once()
    
    def test_dining_suggestions_intent_invalid_location(self):
        event = {
            'currentIntent': {
                'name': 'DiningSuggestionsIntent',
                'slots': {
                    'Location': 'Brooklyn',
                    'Cuisine': 'Italian',
                    'DiningTime': '7:00 PM',
                    'PartySize': '4',
                    'Email': 'test@example.com'
                }
            },
            'sessionAttributes': {}
        }
        
        result = lambda_handler(event, {})
        
        assert result['dialogAction']['type'] == 'ElicitSlot'
        assert result['dialogAction']['slotToElicit'] == 'Location'
        assert 'Manhattan' in result['dialogAction']['message']['content']
    
    def test_unknown_intent(self):
        event = {
            'currentIntent': {
                'name': 'UnknownIntent',
                'slots': {}
            },
            'sessionAttributes': {}
        }
        
        result = lambda_handler(event, {})
        
        assert result['dialogAction']['type'] == 'Close'
        assert result['dialogAction']['fulfillmentState'] == 'Fulfilled'
        assert "didn't understand" in result['dialogAction']['message']['content']
