import pytest
import json
import os
from unittest.mock import patch, MagicMock
import sys
sys.path.append('..')

from lambda_function import (
    lambda_handler,
    process_dining_request,
    get_restaurant_recommendations,
    get_restaurant_details_from_dynamodb,
    format_recommendations_email_text,
    format_recommendations_email_html
)

class TestEmailFormatting:
    
    def test_format_recommendations_email_text(self):
        request_data = {
            'cuisine': 'Italian',
            'location': 'Manhattan',
            'dining_time': '7:00 PM',
            'party_size': '4',
            'email': 'test@example.com'
        }
        
        restaurants = [
            {
                'name': 'Test Italian Restaurant',
                'address': '123 Test St, Manhattan, NY',
                'rating': 4.5,
                'review_count': 100,
                'phone': '+1234567890',
                'price': '$$',
                'url': 'https://yelp.com/test'
            }
        ]
        
        result = format_recommendations_email_text(request_data, restaurants)
        
        assert 'Italian Restaurant Recommendations' in result
        assert 'Test Italian Restaurant' in result
        assert '123 Test St' in result
        assert '4.5/5' in result
        assert '+1234567890' in result
    
    def test_format_recommendations_email_html(self):
        request_data = {
            'cuisine': 'Chinese',
            'location': 'Manhattan',
            'dining_time': '8:00 PM',
            'party_size': '2',
            'email': 'test@example.com'
        }
        
        restaurants = [
            {
                'name': 'Test Chinese Restaurant',
                'address': '456 Test Ave, Manhattan, NY',
                'rating': 4.0,
                'review_count': 50,
                'phone': '',
                'price': '$$$',
                'url': ''
            }
        ]
        
        result = format_recommendations_email_html(request_data, restaurants)
        
        assert '<html>' in result
        assert 'Chinese Restaurant Recommendations' in result
        assert 'Test Chinese Restaurant' in result
        assert '456 Test Ave' in result
        assert '4.0/5' in result

class TestRestaurantProcessing:
    
    @patch('lambda_function.get_dynamodb_resource')
    def test_get_restaurant_details_from_dynamodb(self, mock_get_dynamodb):
        mock_dynamodb = MagicMock()
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        mock_table.get_item.return_value = {
            'Item': {
                'name': 'Test Restaurant',
                'address': '123 Test St',
                'rating': 4.5,
                'review_count': 100,
                'phone': '+1234567890',
                'url': 'https://yelp.com/test',
                'price': '$$',
                'categories': ['Italian', 'Restaurants']
            }
        }
        
        result = get_restaurant_details_from_dynamodb(['test-id'], 'test-request-id', 'test-message-id')
        
        assert len(result) == 1
        assert result[0]['name'] == 'Test Restaurant'
        assert result[0]['rating'] == 4.5
        assert result[0]['phone'] == '+1234567890'
    
    @patch('lambda_function.get_dynamodb_resource')
    def test_get_restaurant_details_missing_item(self, mock_get_dynamodb):
        mock_dynamodb = MagicMock()
        mock_get_dynamodb.return_value = mock_dynamodb
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        mock_table.get_item.return_value = {}
        
        result = get_restaurant_details_from_dynamodb(['nonexistent-id'], 'test-request-id', 'test-message-id')
        
        assert len(result) == 0

class TestMessageProcessing:
    
    @patch('lambda_function.get_restaurant_recommendations')
    @patch('lambda_function.get_restaurant_details_from_dynamodb')
    @patch('lambda_function.send_recommendations_email')
    def test_process_dining_request_success(self, mock_send_email, mock_get_details, mock_get_recs):
        mock_get_recs.return_value = ['restaurant-1', 'restaurant-2']
        mock_get_details.return_value = [
            {'name': 'Restaurant 1', 'rating': 4.5},
            {'name': 'Restaurant 2', 'rating': 4.0}
        ]
        
        message = {
            'Body': json.dumps({
                'location': 'Manhattan',
                'cuisine': 'Italian',
                'dining_time': '7:00 PM',
                'party_size': '4',
                'email': 'test@example.com'
            }),
            'MessageId': 'test-msg-id-123'
        }
        
        result = process_dining_request(message, 'test-request-id')
        
        assert result == True
        mock_get_recs.assert_called_once_with('Italian', 'test-request-id', 'test-msg-id-123')
        mock_get_details.assert_called_once_with(['restaurant-1', 'restaurant-2'], 'test-request-id', 'test-msg-id-123')
        mock_send_email.assert_called_once()
    
    @patch('lambda_function.send_no_results_email')
    @patch('lambda_function.get_restaurant_recommendations')
    def test_process_dining_request_no_restaurants(self, mock_get_recs, mock_send_no_results):
        mock_get_recs.return_value = []
        
        message = {
            'Body': json.dumps({
                'location': 'Manhattan',
                'cuisine': 'Martian',
                'dining_time': '7:00 PM',
                'party_size': '4',
                'email': 'test@example.com'
            }),
            'MessageId': 'test-msg-id-456'
        }
        
        result = process_dining_request(message, 'test-request-id')
        
        assert result == True
        mock_send_no_results.assert_called_once()
    
    def test_process_dining_request_missing_fields(self):
        message = {
            'Body': json.dumps({
                'location': 'Manhattan',
                'cuisine': 'Italian'
            }),
            'MessageId': 'test-msg-id-789'
        }
        
        result = process_dining_request(message, 'test-request-id')
        
        assert result == False
    
    def test_process_dining_request_invalid_json(self):
        message = {
            'Body': 'invalid json',
            'MessageId': 'test-msg-id-invalid'
        }
        
        result = process_dining_request(message, 'test-request-id')
        
        assert result == False

class TestLambdaHandler:
    
    @patch.dict(os.environ, {'SQS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'})
    @patch('lambda_function.receive_messages_from_sqs')
    @patch('lambda_function.process_dining_request')
    @patch('lambda_function.delete_message_from_sqs')
    def test_lambda_handler_success(self, mock_delete, mock_process, mock_receive):
        mock_receive.return_value = [
            {
                'MessageId': 'msg-1',
                'ReceiptHandle': 'receipt-1',
                'Body': json.dumps({
                    'location': 'Manhattan',
                    'cuisine': 'Italian',
                    'dining_time': '7:00 PM',
                    'party_size': '4',
                    'email': 'test@example.com'
                })
            }
        ]
        mock_process.return_value = True
        
        result = lambda_handler({}, {})
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['processed'] == 1
        assert body['failed'] == 0
        
        mock_delete.assert_called_once()
    
    @patch.dict(os.environ, {})
    def test_lambda_handler_missing_config(self):
        result = lambda_handler({}, {})
        
        assert result['statusCode'] == 500
        assert 'Configuration error' in result['body']
    
    @patch.dict(os.environ, {'SQS_QUEUE_URL': 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'})
    @patch('lambda_function.receive_messages_from_sqs')
    def test_lambda_handler_no_messages(self, mock_receive):
        mock_receive.return_value = []
        
        result = lambda_handler({}, {})
        
        assert result['statusCode'] == 200
        assert 'No messages processed' in result['body']
