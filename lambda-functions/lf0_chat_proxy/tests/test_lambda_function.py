import pytest
import json
import os
from unittest.mock import patch, MagicMock, Mock
import sys
sys.path.append('..')

from lambda_function import lambda_handler


class TestLambdaHandler:
    """Test the lambda_handler function"""
    
    @patch('lambda_function.lex_client')
    def test_successful_message_processing(self, mock_lex_client):
        """Test successful message processing through Lex"""
        mock_lex_client.recognize_text.return_value = {
            'messages': [
                {
                    'content': 'Hello! How can I help you?',
                    'contentType': 'PlainText'
                }
            ],
            'sessionState': {
                'intent': {
                    'name': 'GreetingIntent'
                }
            }
        }
        
        event = {
            'body': json.dumps({
                'messages': [
                    {
                        'unstructured': {
                            'text': 'Hello'
                        }
                    }
                ]
            }),
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        
        body = json.loads(result['body'])
        assert 'messages' in body
        assert len(body['messages']) > 0
        assert body['messages'][0]['unstructured']['text'] == 'Hello! How can I help you?'
    
    @patch('lambda_function.lex_client')
    def test_missing_messages_in_body(self, mock_lex_client):
        """Test handling of request with missing messages"""
        event = {
            'body': json.dumps({}),
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        assert 'Access-Control-Allow-Origin' in result['headers']
    
    @patch('lambda_function.lex_client')
    def test_empty_message_text(self, mock_lex_client):
        """Test handling of empty message text"""
        event = {
            'body': json.dumps({
                'messages': [
                    {
                        'unstructured': {
                            'text': ''
                        }
                    }
                ]
            }),
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        assert 'Access-Control-Allow-Origin' in result['headers']
    
    @patch('lambda_function.lex_client')
    def test_lex_exception(self, mock_lex_client):
        """Test handling of Lex API exception"""
        mock_lex_client.recognize_text.side_effect = Exception("Lex API error")
        
        event = {
            'body': json.dumps({
                'messages': [
                    {
                        'unstructured': {
                            'text': 'Hello'
                        }
                    }
                ]
            }),
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        assert 'Access-Control-Allow-Origin' in result['headers']
        
        body = json.loads(result['body'])
        assert 'messages' in body
        assert 'trouble' in body['messages'][0]['unstructured']['text'].lower()
    
    def test_invalid_json_body(self):
        """Test handling of invalid JSON in request body"""
        event = {
            'body': 'invalid json',
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        assert result['statusCode'] == 500
        assert 'Access-Control-Allow-Origin' in result['headers']
    
    @patch('lambda_function.lex_client')
    def test_session_id_generation(self, mock_lex_client):
        """Test that session ID is generated from source IP"""
        mock_lex_client.recognize_text.return_value = {
            'messages': [{'content': 'test', 'contentType': 'PlainText'}]
        }
        
        event = {
            'body': json.dumps({
                'messages': [
                    {
                        'unstructured': {
                            'text': 'test'
                        }
                    }
                ]
            }),
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.100'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        # Check that Lex was called with a session ID
        assert mock_lex_client.recognize_text.called
        call_kwargs = mock_lex_client.recognize_text.call_args[1]
        assert 'sessionId' in call_kwargs
        assert call_kwargs['sessionId'].startswith('session-')
    
    @patch('lambda_function.lex_client')
    def test_cors_headers(self, mock_lex_client):
        """Test that proper CORS headers are included"""
        mock_lex_client.recognize_text.return_value = {
            'messages': [{'content': 'test', 'contentType': 'PlainText'}]
        }
        
        event = {
            'body': json.dumps({
                'messages': [
                    {
                        'unstructured': {
                            'text': 'test'
                        }
                    }
                ]
            }),
            'requestContext': {
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        mock_context = Mock()
        result = lambda_handler(event, mock_context)
        
        assert 'headers' in result
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Headers' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']
        assert result['headers']['Access-Control-Allow-Origin'] == '*'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
