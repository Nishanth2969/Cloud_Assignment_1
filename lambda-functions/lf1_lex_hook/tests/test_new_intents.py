"""
Tests for new conversational intents added to LF1 Lex Hook
These tests use Lex V2 format
"""
import pytest
import json
import sys
sys.path.append('..')

from lambda_function import lambda_handler


class TestNewIntents:
    """Test suite for new conversational intents"""
    
    def test_help_intent(self):
        """Test HelpIntent provides guidance to users"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'cuisine' in result['messages'][0]['content'].lower()
        assert 'help' in result['messages'][0]['content'].lower() or 'find' in result['messages'][0]['content'].lower()
    
    def test_cancel_intent(self):
        """Test CancelIntent cancels user request"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'cancel' in result['messages'][0]['content'].lower() or 'problem' in result['messages'][0]['content'].lower()
    
    def test_change_mind_intent(self):
        """Test ChangeMindIntent starts fresh conversation"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'ChangeMindIntent',
                    'slots': {}
                },
                'sessionAttributes': {'some_key': 'some_value'}
            }
        }
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        # Should clear session attributes
        assert result['sessionState']['sessionAttributes'] == {}
        assert 'start' in result['messages'][0]['content'].lower() or 'cuisine' in result['messages'][0]['content'].lower()
    
    def test_restaurant_types_intent(self):
        """Test RestaurantTypesIntent lists available cuisines"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        message = result['messages'][0]['content'].lower()
        # Should mention multiple cuisines
        assert 'italian' in message or 'chinese' in message or 'thai' in message
        assert 'indian' in message or 'french' in message or 'japanese' in message
    
    def test_location_intent(self):
        """Test LocationIntent explains coverage area"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'manhattan' in result['messages'][0]['content'].lower()
    
    def test_feedback_intent(self):
        """Test FeedbackIntent acknowledges user feedback"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        assert 'feedback' in result['messages'][0]['content'].lower() or 'thank' in result['messages'][0]['content'].lower()
    
    def test_enhanced_greeting_intent(self):
        """Test enhanced GreetingIntent with better response"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        message = result['messages'][0]['content'].lower()
        assert 'concierge' in message or 'help' in message or 'restaurant' in message
    
    def test_enhanced_thank_you_intent(self):
        """Test enhanced ThankYouIntent with better response"""
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
        
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        assert result['sessionState']['intent']['state'] == 'Fulfilled'
        message = result['messages'][0]['content'].lower()
        assert 'welcome' in message or 'enjoy' in message


class TestIntentResponseQuality:
    """Test the quality and consistency of intent responses"""
    
    def test_all_intents_return_valid_structure(self):
        """Ensure all intents return valid Lex V2 response structure"""
        intents = [
            'HelpIntent', 'CancelIntent', 'ChangeMindIntent',
            'RestaurantTypesIntent', 'LocationIntent', 'FeedbackIntent',
            'GreetingIntent', 'ThankYouIntent'
        ]
        
        for intent_name in intents:
            event = {
                'invocationSource': 'FulfillmentCodeHook',
                'sessionState': {
                    'intent': {
                        'name': intent_name,
                        'slots': {}
                    },
                    'sessionAttributes': {}
                }
            }
            
            result = lambda_handler(event, {})
            
            # Validate structure
            assert 'sessionState' in result
            assert 'dialogAction' in result['sessionState']
            assert 'type' in result['sessionState']['dialogAction']
            assert 'intent' in result['sessionState']
            assert 'state' in result['sessionState']['intent']
            assert 'messages' in result
            assert len(result['messages']) > 0
            assert 'content' in result['messages'][0]
            
            # Validate response is not empty
            assert len(result['messages'][0]['content']) > 10
            
            print(f"✓ {intent_name} returns valid structure")
    
    def test_intents_are_conversational(self):
        """Ensure responses feel natural and conversational"""
        conversational_intents = {
            'HelpIntent': ['help', 'can', 'cuisine'],
            'CancelIntent': ['cancel', 'problem', 'anytime'],
            'GreetingIntent': ['hi', 'help', 'restaurant'],
            'ThankYouIntent': ['welcome', 'enjoy', 'anytime']
        }
        
        for intent_name, expected_words in conversational_intents.items():
            event = {
                'invocationSource': 'FulfillmentCodeHook',
                'sessionState': {
                    'intent': {
                        'name': intent_name,
                        'slots': {}
                    },
                    'sessionAttributes': {}
                }
            }
            
            result = lambda_handler(event, {})
            message = result['messages'][0]['content'].lower()
            
            # Check if at least one expected word is present
            assert any(word in message for word in expected_words), \
                f"{intent_name} response should contain one of {expected_words}, got: {message}"
            
            print(f"✓ {intent_name} is conversational")


class TestErrorHandling:
    """Test error handling for new intents"""
    
    def test_fallback_intent_enhanced_message(self):
        """Test enhanced fallback message"""
        event = {
            'invocationSource': 'FulfillmentCodeHook',
            'sessionState': {
                'intent': {
                    'name': 'UnknownIntentName',
                    'slots': {}
                },
                'sessionAttributes': {}
            }
        }
        
        # This should trigger the exception handler
        result = lambda_handler(event, {})
        
        assert result['sessionState']['dialogAction']['type'] == 'Close'
        message = result['messages'][0]['content'].lower()
        assert 'sorry' in message or 'understand' in message or 'help' in message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


