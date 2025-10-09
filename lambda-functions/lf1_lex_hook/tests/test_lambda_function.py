import pytest
import json
import os
from unittest.mock import patch, MagicMock, Mock
import sys
sys.path.append('..')

from lambda_function import lambda_handler, get_slot_value, close


class TestLexHookFunctions:
    """Test LF1 Lex Hook functions"""
    
    def test_get_slot_value_with_value(self):
        """Test getting slot value when it exists"""
        slots = {
            'Cuisine': {
                'value': {
                    'interpretedValue': 'Italian'
                }
            }
        }
        
        result = get_slot_value(slots, 'Cuisine')
        assert result == 'Italian'
    
    def test_get_slot_value_missing_slot(self):
        """Test getting slot value when slot doesn't exist"""
        slots = {}
        
        result = get_slot_value(slots, 'Cuisine')
        assert result is None
    
    def test_get_slot_value_null_slot(self):
        """Test getting slot value when slot is null"""
        slots = {
            'Cuisine': None
        }
        
        result = get_slot_value(slots, 'Cuisine')
        assert result is None
    
    def test_close_function_fulfilled(self):
        """Test close function with fulfilled state"""
        result = close(
            {'key': 'value'},
            'GreetingIntent',
            'Fulfilled',
            'Hello!'
        )
        
        assert 'sessionState' in result
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['name'] == 'GreetingIntent'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert result['messages'][0]['content'] == 'Hello!'


class TestDiningSuggestionsIntent:
    """Test DiningSuggestionsIntent handling"""
    
    @patch('lambda_function.boto3')
    def test_dining_suggestions_all_slots_filled(self, mock_boto3):
        """Test DiningSuggestionsIntent with all 5 slots filled including Location"""
        mock_sqs = Mock()
        mock_sqs.send_message.return_value = {'MessageId': 'test-123'}
        mock_boto3.client.return_value = mock_sqs
        
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'DiningSuggestionsIntent',
                    'slots': {
                        'Location': {
                            'value': {
                                'interpretedValue': 'Manhattan'
                            }
                        },
                        'Cuisine': {
                            'value': {
                                'originalValue': 'Italian',
                                'interpretedValue': 'italian'
                            }
                        },
                        'DiningTime': {
                            'value': {
                                'interpretedValue': '7 PM'
                            }
                        },
                        'PartySize': {
                            'value': {
                                'interpretedValue': '2'
                            }
                        },
                        'Email': {
                            'value': {
                                'interpretedValue': 'test@example.com'
                            }
                        }
                    }
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'suggestions shortly' in result['messages'][0]['content'].lower()
        
        # Verify Location was sent to SQS
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args[1]['MessageBody'])
        assert message_body['location'] == 'Manhattan'
    
    def test_dining_suggestions_missing_slots(self):
        """Test DiningSuggestionsIntent with missing slots (including Location)"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'DiningSuggestionsIntent',
                    'slots': {
                        'Location': None,
                        'Cuisine': {
                            'value': {
                                'originalValue': 'Italian'
                            }
                        },
                        'DiningTime': None,
                        'PartySize': None,
                        'Email': None
                    }
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        # Should delegate back to Lex to collect remaining slots
        assert result['sessionState']['dialogAction']['type'] == 'Delegate'
    
    @patch('lambda_function.boto3')
    def test_dining_suggestions_with_location_verification(self, mock_boto3):
        """Test that Location slot is properly collected and sent to SQS"""
        mock_sqs = Mock()
        mock_sqs.send_message.return_value = {'MessageId': 'test-456'}
        mock_boto3.client.return_value = mock_sqs
        
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'DiningSuggestionsIntent',
                    'slots': {
                        'Location': {
                            'value': {
                                'interpretedValue': 'Brooklyn'
                            }
                        },
                        'Cuisine': {
                            'value': {
                                'originalValue': 'Chinese',
                                'interpretedValue': 'chinese'
                            }
                        },
                        'DiningTime': {
                            'value': {
                                'interpretedValue': '8 PM'
                            }
                        },
                        'PartySize': {
                            'value': {
                                'interpretedValue': '4'
                            }
                        },
                        'Email': {
                            'value': {
                                'interpretedValue': 'user@test.com'
                            }
                        }
                    }
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        # Verify the message was sent
        assert mock_sqs.send_message.called
        
        # Extract and verify the message content
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args[1]['MessageBody'])
        
        # Verify all 5 required parameters are present
        assert 'location' in message_body
        assert 'cuisine' in message_body
        assert 'dining_time' in message_body
        assert 'party_size' in message_body
        assert 'email' in message_body
        
        # Verify Location value is correct
        assert message_body['location'] == 'Brooklyn'
        assert message_body['cuisine'] == 'Chinese'


class TestGreetingIntent:
    """Test GreetingIntent handling"""
    
    def test_greeting_intent(self):
        """Test GreetingIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'GreetingIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'dining concierge' in result['messages'][0]['content'].lower()


class TestThankYouIntent:
    """Test ThankYouIntent handling"""
    
    def test_thankyou_intent(self):
        """Test ThankYouIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'ThankYouIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'welcome' in result['messages'][0]['content'].lower()


class TestNewIntents:
    """Test newly added intents"""
    
    def test_help_intent(self):
        """Test HelpIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'HelpIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'cuisine' in result['messages'][0]['content'].lower()
    
    def test_cancel_intent(self):
        """Test CancelIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'CancelIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'cancelled' in result['messages'][0]['content'].lower()
    
    def test_changemind_intent(self):
        """Test ChangeMindIntent response (should clear session)"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'ChangeMindIntent',
                    'slots': {}
                },
                'sessionAttributes': {'test': 'value'}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        # Session should be cleared
        assert result['sessionState']['sessionAttributes'] == {}
    
    def test_restaurant_types_intent(self):
        """Test RestaurantTypesIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'RestaurantTypesIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        content = result['messages'][0]['content'].lower()
        assert 'italian' in content or 'chinese' in content
    
    def test_location_intent(self):
        """Test LocationIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'LocationIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'manhattan' in result['messages'][0]['content'].lower()
    
    def test_feedback_intent(self):
        """Test FeedbackIntent response"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'FeedbackIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'feedback' in result['messages'][0]['content'].lower()


class TestUnknownIntent:
    """Test unknown intent handling"""
    
    def test_unknown_intent(self):
        """Test handling of unknown intent"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'UnknownIntent',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        result = lambda_handler(event, None)
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        # Should have a fallback response
        assert len(result['messages']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
