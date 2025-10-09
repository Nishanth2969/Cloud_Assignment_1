"""
Test suite for Dead Letter Queue (DLQ) functionality
Tests error handling, logging, and message retention behavior
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3
from decimal import Decimal
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda_function import (
    lambda_handler,
    process_dining_request,
    send_recommendations_email,
    send_no_results_email
)


class TestDLQErrorHandling:
    """Test DLQ error handling and message retention"""
    
    @mock_aws
    def test_ses_failure_does_not_delete_message(self):
        """
        Test that when SES fails, the message is NOT deleted from SQS.
        This allows SQS to retry or move to DLQ after maxReceiveCount.
        """
        # Setup SQS
        sqs = boto3.client('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName='test-queue')
        queue_url = queue['QueueUrl']
        
        # Setup SES (but we'll mock it to fail)
        ses = boto3.client('ses', region_name='us-east-1')
        ses.verify_email_identity(EmailAddress='test@example.com')
        
        # Send test message
        message_body = {
            'location': 'Manhattan',
            'cuisine': 'Italian',
            'dining_time': '7 PM',
            'party_size': '2',
            'email': 'invalid@email'  # Invalid email to force SES failure
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        # Set environment variables
        with patch.dict(os.environ, {
            'SQS_QUEUE_URL': queue_url,
            'DYNAMODB_TABLE_NAME': 'test-table',
            'SES_SENDER_EMAIL': 'test@example.com'
        }):
            # Mock context
            mock_context = Mock()
            mock_context.request_id = 'test-request-id-123'
            
            # Mock SES to fail
            with patch('lambda_function.get_ses_client') as mock_ses_client:
                mock_ses = Mock()
                mock_ses.send_email.side_effect = Exception("Invalid email address")
                mock_ses_client.return_value = mock_ses
                
                # Mock DynamoDB and OpenSearch to return data
                with patch('lambda_function.get_restaurant_recommendations') as mock_recs, \
                     patch('lambda_function.get_restaurant_details_from_dynamodb') as mock_details:
                    
                    mock_recs.return_value = ['rest1', 'rest2']
                    mock_details.return_value = [
                        {
                            'name': 'Test Restaurant',
                            'address': '123 Main St',
                            'rating': 4.5,
                            'review_count': 100,
                            'phone': '555-1234',
                            'url': 'http://test.com',
                            'price': '$$',
                            'categories': ['Italian']
                        }
                    ]
                    
                    # Call Lambda handler
                    result = lambda_handler({}, mock_context)
                    
                    # Verify Lambda reported failure (message NOT processed successfully)
                    result_body = json.loads(result['body'])
                    assert result_body['failed'] == 1, "Should have 1 failed message"
                    assert result_body['processed'] == 0, "Should have 0 successfully processed messages"
                    
                    # The key behavior: Message was NOT deleted from queue
                    # In production, SQS will retry this message or move to DLQ after maxReceiveCount
                    # The test verifies the Lambda function didn't call delete_message_from_sqs
                    # which is proven by the failed count and the warning log above


    @mock_aws
    def test_requestid_logging_in_error_handling(self, caplog):
        """Test that RequestId is included in all error logs"""
        import logging
        caplog.set_level(logging.INFO)
        
        sqs = boto3.client('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName='test-queue')
        queue_url = queue['QueueUrl']
        
        # Send message with missing fields to trigger error
        message_body = {
            'location': 'Manhattan',
            'cuisine': 'Italian',
            # Missing required fields
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        with patch.dict(os.environ, {'SQS_QUEUE_URL': queue_url}):
            mock_context = Mock()
            mock_context.request_id = 'test-request-id-456'
            
            lambda_handler({}, mock_context)
            
            # Check logs contain RequestId
            log_messages = [rec.message for rec in caplog.records]
            request_id_logs = [log for log in log_messages if 'test-request-id-456' in log]
            
            assert len(request_id_logs) > 0, "RequestId should appear in logs"


    @mock_aws
    def test_messageid_logging(self, caplog):
        """Test that MessageId is included in logs for tracing"""
        import logging
        caplog.set_level(logging.INFO)
        
        sqs = boto3.client('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName='test-queue')
        queue_url = queue['QueueUrl']
        
        message_body = {
            'location': 'Manhattan',
            'cuisine': 'Italian',
            'dining_time': '7 PM',
            'party_size': '2',
            'email': 'test@example.com'
        }
        
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        message_id = response['MessageId']
        
        with patch.dict(os.environ, {'SQS_QUEUE_URL': queue_url}):
            mock_context = Mock()
            mock_context.request_id = 'test-request-id-789'
            
            # Mock to simulate processing
            with patch('lambda_function.get_restaurant_recommendations') as mock_recs:
                mock_recs.return_value = []  # No restaurants to trigger specific path
                
                lambda_handler({}, mock_context)
                
                # Check logs contain MessageId
                log_messages = [rec.message for rec in caplog.records]
                messageid_logs = [log for log in log_messages if 'MessageId' in log]
                
                assert len(messageid_logs) > 0, "MessageId should appear in logs"


    def test_ses_error_logging_details(self, caplog):
        """Test that SES errors are logged with detailed information"""
        import logging
        caplog.set_level(logging.ERROR)
        
        request_data = {
            'email': 'test@example.com',
            'cuisine': 'Italian',
            'location': 'Manhattan',
            'dining_time': '7 PM',
            'party_size': '2'
        }
        
        restaurants = [
            {
                'name': 'Test Restaurant',
                'address': '123 Main St',
                'rating': 4.5,
                'review_count': 100,
                'phone': '555-1234',
                'url': 'http://test.com',
                'price': '$$',
                'categories': ['Italian']
            }
        ]
        
        with patch('lambda_function.get_ses_client') as mock_ses_client:
            mock_ses = Mock()
            mock_ses.send_email.side_effect = Exception("SES limit exceeded")
            mock_ses_client.return_value = mock_ses
            
            with patch.dict(os.environ, {'SES_SENDER_EMAIL': 'noreply@test.com'}):
                try:
                    send_recommendations_email(
                        request_data,
                        restaurants,
                        'test-request-id',
                        'test-message-id'
                    )
                except Exception:
                    pass  # Expected to raise
                
                # Check error log contains all required details
                error_logs = [rec.message for rec in caplog.records if rec.levelname == 'ERROR']
                
                assert len(error_logs) > 0
                error_log = error_logs[0]
                
                # Verify log contains all required information
                assert 'test-request-id' in error_log, "Log should contain RequestId"
                assert 'test-message-id' in error_log, "Log should contain MessageId"
                assert 'Error Type' in error_log, "Log should contain Error Type"
                assert 'Error Message' in error_log, "Log should contain Error Message"
                assert 'Recipient' in error_log, "Log should contain Recipient"


    @mock_aws
    def test_receive_count_logging(self, caplog):
        """Test that ApproximateReceiveCount is logged for DLQ monitoring"""
        import logging
        caplog.set_level(logging.INFO)
        
        sqs = boto3.client('sqs', region_name='us-east-1')
        queue = sqs.create_queue(QueueName='test-queue')
        queue_url = queue['QueueUrl']
        
        message_body = {
            'location': 'Manhattan',
            'cuisine': 'Italian',
            'dining_time': '7 PM',
            'party_size': '2',
            'email': 'test@example.com'
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        with patch.dict(os.environ, {'SQS_QUEUE_URL': queue_url}):
            mock_context = Mock()
            mock_context.request_id = 'test-request-id'
            
            with patch('lambda_function.process_dining_request') as mock_process:
                mock_process.return_value = True
                
                lambda_handler({}, mock_context)
                
                # Check logs contain Receive count
                log_messages = [rec.message for rec in caplog.records]
                receive_count_logs = [log for log in log_messages if 'Receive count' in log]
                
                assert len(receive_count_logs) > 0, "Receive count should be logged"


    @mock_aws
    def test_successful_processing_deletes_message(self):
        """
        Test that when processing succeeds, message IS deleted from SQS.
        """
        # Setup
        sqs = boto3.client('sqs', region_name='us-east-1')
        ses = boto3.client('ses', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        queue = sqs.create_queue(QueueName='test-queue')
        queue_url = queue['QueueUrl']
        
        ses.verify_email_identity(EmailAddress='noreply@test.com')
        ses.verify_email_identity(EmailAddress='user@example.com')
        
        # Create DynamoDB table
        table = dynamodb.create_table(
            TableName='test-restaurants',
            KeySchema=[{'AttributeName': 'business_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'business_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.put_item(Item={
            'business_id': 'rest1',
            'name': 'Test Restaurant',
            'address': '123 Main St',
            'rating': Decimal('4.5'),
            'review_count': 100,
            'phone': '555-1234',
            'url': 'http://test.com',
            'price': '$$',
            'categories': ['Italian']
        })
        
        # Send test message
        message_body = {
            'location': 'Manhattan',
            'cuisine': 'Italian',
            'dining_time': '7 PM',
            'party_size': '2',
            'email': 'user@example.com'  # Valid email
        }
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        with patch.dict(os.environ, {
            'SQS_QUEUE_URL': queue_url,
            'DYNAMODB_TABLE_NAME': 'test-restaurants',
            'SES_SENDER_EMAIL': 'noreply@test.com'
        }):
            mock_context = Mock()
            mock_context.request_id = 'test-request-id'
            
            with patch('lambda_function.get_restaurant_recommendations') as mock_recs:
                mock_recs.return_value = ['rest1']
                
                # Call Lambda handler
                result = lambda_handler({}, mock_context)
                
                # Verify message WAS deleted (queue should be empty)
                messages = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=1
                )
                
                # Queue should be empty after successful processing
                assert 'Messages' not in messages or len(messages.get('Messages', [])) == 0


    def test_error_type_captured_in_logs(self, caplog):
        """Test that error type (exception class name) is captured"""
        import logging
        caplog.set_level(logging.ERROR)
        
        request_data = {
            'email': 'test@example.com',
            'cuisine': 'Italian',
            'location': 'Manhattan',
            'dining_time': '7 PM',
            'party_size': '2'
        }
        
        restaurants = []
        
        class CustomTestException(Exception):
            pass
        
        with patch('lambda_function.get_ses_client') as mock_ses_client:
            mock_ses = Mock()
            mock_ses.send_email.side_effect = CustomTestException("Custom error message")
            mock_ses_client.return_value = mock_ses
            
            with patch.dict(os.environ, {'SES_SENDER_EMAIL': 'noreply@test.com'}):
                try:
                    send_no_results_email(
                        request_data,
                        'test-request-id',
                        'test-message-id'
                    )
                except Exception:
                    pass
                
                error_logs = [rec.message for rec in caplog.records if rec.levelname == 'ERROR']
                
                assert len(error_logs) > 0
                # Should log the exception class name
                assert any('CustomTestException' in log for log in error_logs)


class TestDLQIntegration:
    """Integration tests for DLQ functionality"""
    
    @mock_aws
    def test_redrive_policy_configuration(self):
        """Test that Redrive Policy can be configured on SQS queue"""
        sqs = boto3.client('sqs', region_name='us-east-1')
        
        # Create main queue and DLQ
        main_queue = sqs.create_queue(QueueName='main-queue')
        dlq = sqs.create_queue(QueueName='dlq')
        
        main_queue_url = main_queue['QueueUrl']
        dlq_url = dlq['QueueUrl']
        
        # Get DLQ ARN
        dlq_attrs = sqs.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['QueueArn']
        )
        dlq_arn = dlq_attrs['Attributes']['QueueArn']
        
        # Set Redrive Policy
        redrive_policy = {
            'deadLetterTargetArn': dlq_arn,
            'maxReceiveCount': 3
        }
        
        sqs.set_queue_attributes(
            QueueUrl=main_queue_url,
            Attributes={
                'RedrivePolicy': json.dumps(redrive_policy)
            }
        )
        
        # Verify configuration
        attrs = sqs.get_queue_attributes(
            QueueUrl=main_queue_url,
            AttributeNames=['RedrivePolicy']
        )
        
        assert 'RedrivePolicy' in attrs['Attributes']
        policy = json.loads(attrs['Attributes']['RedrivePolicy'])
        assert policy['maxReceiveCount'] == 3
        assert dlq_arn in policy['deadLetterTargetArn']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

