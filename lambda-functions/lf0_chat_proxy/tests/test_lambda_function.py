import pytest
import json
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.append('..')

from lambda_function import lambda_handler, send_to_lex, cors_response

class TestLambdaHandler:
    
    def test_options_request(self):
        event = {
            'httpMethod': 'OPTIONS',
            'body': ''
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_invalid_http_method(self):
        event = {
            'httpMethod': 'GET',
            'body': ''
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 405
        body = json.loads(result['body'])
        assert 'Method not allowed' in body['error']
    
    def test_missing_message(self):
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Message is required' in body['error']
    
    def test_empty_message(self):
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'message': '   '})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Message is required' in body['error']
    
    def test_message_too_long(self):
        long_message = 'a' * 1001
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'message': long_message})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Message too long' in body['error']
    
    def test_invalid_json(self):
        event = {
            'httpMethod': 'POST',
            'body': 'invalid json'
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'Invalid JSON' in body['error']
    
    @patch('lambda_function.send_to_lex')
    def test_successful_message_processing(self, mock_send_to_lex):
        mock_send_to_lex.return_value = {
            'message': 'Hello! How can I help you?',
            'sessionId': 'test-session',
            'intentName': 'GreetingIntent',
            'slots': {}
        }
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'message': 'Hello',
                'sessionId': 'test-session'
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['message'] == 'Hello! How can I help you?'
        assert body['sessionId'] == 'test-session'
        assert body['intentName'] == 'GreetingIntent'
        mock_send_to_lex.assert_called_once_with('Hello', 'test-session')
    
    @patch('lambda_function.send_to_lex')
    def test_lex_failure(self, mock_send_to_lex):
        mock_send_to_lex.return_value = None
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'message': 'Hello'})
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'Failed to process message' in body['error']
    
    def test_default_session_id(self):
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'message': 'Hello'})
        }
        
        with patch('lambda_function.send_to_lex') as mock_send_to_lex:
            mock_send_to_lex.return_value = {
                'message': 'Response',
                'sessionId': 'default-session',
                'intentName': '',
                'slots': {}
            }
            
            lambda_handler(event, {})
            
            mock_send_to_lex.assert_called_once_with('Hello', 'default-session')

class TestSendToLex:
    
    @patch.dict(os.environ, {
        'LEX_BOT_ID': 'test-bot-id',
        'LEX_BOT_ALIAS_ID': 'test-alias',
        'LEX_LOCALE_ID': 'en_US'
    })
    @patch('lambda_function.get_lex_client')
    def test_successful_lex_call(self, mock_get_lex_client):
        mock_lex_client = MagicMock()
        mock_get_lex_client.return_value = mock_lex_client
        mock_lex_client.recognize_text.return_value = {
            'messages': [{'content': 'Hello! How can I help you?'}],
            'sessionState': {
                'intent': {
                    'name': 'GreetingIntent',
                    'slots': {
                        'TestSlot': {
                            'value': {
                                'interpretedValue': 'test_value'
                            }
                        }
                    }
                }
            }
        }
        
        result = send_to_lex('Hello', 'test-session')
        
        assert result is not None
        assert result['message'] == 'Hello! How can I help you?'
        assert result['sessionId'] == 'test-session'
        assert result['intentName'] == 'GreetingIntent'
        assert result['slots']['TestSlot'] == 'test_value'
        
        mock_lex_client.recognize_text.assert_called_once_with(
            botId='test-bot-id',
            botAliasId='test-alias',
            localeId='en_US',
            sessionId='test-session',
            text='Hello'
        )
    
    @patch.dict(os.environ, {})
    def test_missing_bot_id(self):
        result = send_to_lex('Hello', 'test-session')
        
        assert result is None
    
    @patch.dict(os.environ, {'LEX_BOT_ID': 'test-bot-id'})
    @patch('lambda_function.get_lex_client')
    def test_lex_client_exception(self, mock_get_lex_client):
        mock_lex_client = MagicMock()
        mock_get_lex_client.return_value = mock_lex_client
        mock_lex_client.recognize_text.side_effect = Exception('Lex error')
        
        result = send_to_lex('Hello', 'test-session')
        
        assert result is None
    
    @patch.dict(os.environ, {'LEX_BOT_ID': 'test-bot-id'})
    @patch('lambda_function.get_lex_client')
    def test_empty_lex_response(self, mock_get_lex_client):
        mock_lex_client = MagicMock()
        mock_get_lex_client.return_value = mock_lex_client
        mock_lex_client.recognize_text.return_value = {}
        
        result = send_to_lex('Hello', 'test-session')
        
        assert result is not None
        assert "I'm sorry, I didn't understand" in result['message']
        assert result['sessionId'] == 'test-session'
        assert result['intentName'] == ''
        assert result['slots'] == {}
    
    @patch.dict(os.environ, {'LEX_BOT_ID': 'test-bot-id'})
    @patch('lambda_function.get_lex_client')
    def test_default_values(self, mock_get_lex_client):
        mock_lex_client = MagicMock()
        mock_get_lex_client.return_value = mock_lex_client
        mock_lex_client.recognize_text.return_value = {
            'messages': [{'content': 'Test response'}]
        }
        
        result = send_to_lex('Hello', 'test-session')
        
        mock_lex_client.recognize_text.assert_called_once_with(
            botId='test-bot-id',
            botAliasId='TSTALIASID',
            localeId='en_US',
            sessionId='test-session',
            text='Hello'
        )

class TestCorsResponse:
    
    def test_cors_headers_present(self):
        result = cors_response(200, {'message': 'test'})
        
        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Headers' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_json_body(self):
        test_body = {'message': 'test', 'data': [1, 2, 3]}
        result = cors_response(200, test_body)
        
        parsed_body = json.loads(result['body'])
        assert parsed_body == test_body
    
    def test_different_status_codes(self):
        for status_code in [200, 400, 404, 500]:
            result = cors_response(status_code, {'status': status_code})
            assert result['statusCode'] == status_code

class TestIntegration:
    
    @patch.dict(os.environ, {'LEX_BOT_ID': 'test-bot-id'})
    @patch('lambda_function.get_lex_client')
    def test_full_request_flow(self, mock_get_lex_client):
        mock_lex_client = MagicMock()
        mock_get_lex_client.return_value = mock_lex_client
        mock_lex_client.recognize_text.return_value = {
            'messages': [{'content': 'I can help you find restaurants!'}],
            'sessionState': {
                'intent': {
                    'name': 'DiningSuggestionsIntent',
                    'slots': {
                        'Cuisine': {
                            'value': {
                                'interpretedValue': 'Italian'
                            }
                        }
                    }
                }
            }
        }
        
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'message': 'I want Italian food',
                'sessionId': 'user-123'
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert 'restaurants' in body['message']
        assert body['sessionId'] == 'user-123'
        assert body['intentName'] == 'DiningSuggestionsIntent'
        assert body['slots']['Cuisine'] == 'Italian'
