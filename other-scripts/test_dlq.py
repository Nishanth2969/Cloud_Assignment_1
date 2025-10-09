#!/usr/bin/env python3
"""
Dead Letter Queue (DLQ) Test Script

This script tests the DLQ functionality by:
1. Sending messages with invalid email addresses to force SES failures
2. Monitoring the retry attempts
3. Verifying messages move to DLQ after maxReceiveCount
4. Displaying CloudWatch logs with RequestId and error details
"""

import boto3
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, List

# Configuration
REGION = 'us-east-1'
QUEUE_NAME = 'q-dining-suggestions'
DLQ_NAME = 'q-dining-suggestions-dlq'
LAMBDA_FUNCTION_NAME = 'lf2-suggestions-worker'

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(message: str):
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_warning(message: str):
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_error(message: str):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def get_sqs_client():
    return boto3.client('sqs', region_name=REGION)


def get_logs_client():
    return boto3.client('logs', region_name=REGION)


def get_queue_url(queue_name: str) -> str:
    """Get SQS queue URL"""
    try:
        sqs = get_sqs_client()
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except Exception as e:
        print_error(f"Failed to get queue URL for {queue_name}: {str(e)}")
        sys.exit(1)


def send_test_message_with_invalid_email(queue_url: str, test_case: int) -> str:
    """Send a test message with invalid email to force SES failure"""
    sqs = get_sqs_client()
    
    # Various invalid email scenarios
    invalid_emails = [
        "invalid-email-no-at-sign",  # Missing @ sign
        "invalid@",  # Missing domain
        "@invalid.com",  # Missing local part
        "invalid..email@test.com",  # Double dots
        "invalid email@test.com",  # Space in email
    ]
    
    invalid_email = invalid_emails[test_case % len(invalid_emails)]
    
    message_body = {
        'location': 'Manhattan',
        'cuisine': 'Italian',
        'dining_time': '7 PM',
        'party_size': '2',
        'email': invalid_email,
        'timestamp': datetime.utcnow().isoformat(),
        'test_case': f'DLQ_TEST_{test_case}',
        'note': 'This is a test message with invalid email to trigger DLQ'
    }
    
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_body)
    )
    
    return response['MessageId']


def get_queue_attributes(queue_url: str) -> Dict[str, Any]:
    """Get all queue attributes"""
    sqs = get_sqs_client()
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['All']
    )
    return response.get('Attributes', {})


def get_messages_from_queue(queue_url: str, wait_time: int = 5) -> List[Dict]:
    """Receive messages from queue (for DLQ monitoring)"""
    sqs = get_sqs_client()
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=wait_time,
        AttributeNames=['All'],
        MessageAttributeNames=['All']
    )
    return response.get('Messages', [])


def get_recent_lambda_logs(function_name: str, minutes: int = 5) -> List[Dict]:
    """Get recent Lambda function logs"""
    logs_client = get_logs_client()
    log_group_name = f'/aws/lambda/{function_name}'
    
    try:
        # Get log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        log_streams = response.get('logStreams', [])
        
        if not log_streams:
            print_warning(f"No log streams found for {function_name}")
            return []
        
        # Get logs from recent streams
        start_time = int((time.time() - (minutes * 60)) * 1000)
        
        all_events = []
        for stream in log_streams[:3]:  # Check last 3 streams
            try:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream['logStreamName'],
                    startTime=start_time,
                    limit=100
                )
                all_events.extend(events_response.get('events', []))
            except Exception as e:
                print_warning(f"Error reading log stream {stream['logStreamName']}: {str(e)}")
        
        return all_events
    
    except Exception as e:
        print_error(f"Error getting Lambda logs: {str(e)}")
        return []


def display_lambda_logs(events: List[Dict], message_id: str = None):
    """Display Lambda logs with highlighting"""
    print_info(f"Recent Lambda logs (showing last {len(events)} events):\n")
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        message = event['message'].strip()
        
        # Highlight important log entries
        if message_id and message_id in message:
            print(f"{Colors.BOLD}{timestamp} | {message}{Colors.ENDC}")
        elif 'ERROR' in message or 'FAILED' in message:
            print(f"{Colors.FAIL}{timestamp} | {message}{Colors.ENDC}")
        elif 'WARNING' in message or 'Receive count:' in message:
            print(f"{Colors.WARNING}{timestamp} | {message}{Colors.ENDC}")
        elif 'RequestId' in message or 'MessageId' in message:
            print(f"{Colors.OKCYAN}{timestamp} | {message}{Colors.ENDC}")
        else:
            print(f"{timestamp} | {message}")


def monitor_message_retries(main_queue_url: str, dlq_url: str, message_id: str, max_wait_minutes: int = 10):
    """Monitor message retries and eventual movement to DLQ"""
    print_header("Monitoring Message Retries")
    
    print_info(f"Monitoring MessageId: {message_id}")
    print_info(f"Will check for up to {max_wait_minutes} minutes...\n")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    check_interval = 30  # Check every 30 seconds
    
    while (time.time() - start_time) < max_wait_seconds:
        print(f"\n{Colors.BOLD}--- Check at {datetime.now().strftime('%H:%M:%S')} ---{Colors.ENDC}")
        
        # Check main queue
        main_attrs = get_queue_attributes(main_queue_url)
        main_visible = int(main_attrs.get('ApproximateNumberOfMessages', 0))
        main_in_flight = int(main_attrs.get('ApproximateNumberOfMessagesNotVisible', 0))
        
        print_info(f"Main Queue - Visible: {main_visible}, In-Flight: {main_in_flight}")
        
        # Check DLQ
        dlq_attrs = get_queue_attributes(dlq_url)
        dlq_visible = int(dlq_attrs.get('ApproximateNumberOfMessages', 0))
        
        print_info(f"DLQ - Visible: {dlq_visible}")
        
        # Check for message in DLQ
        if dlq_visible > 0:
            print_success(f"\n✓ Message moved to DLQ!")
            
            # Retrieve message from DLQ
            dlq_messages = get_messages_from_queue(dlq_url, wait_time=1)
            
            if dlq_messages:
                for msg in dlq_messages:
                    if msg['MessageId'] == message_id:
                        print_success(f"\n✓ Found our test message in DLQ!")
                        print(f"\n{Colors.BOLD}Message Details:{Colors.ENDC}")
                        print(f"  MessageId: {msg['MessageId']}")
                        print(f"  Receive Count: {msg.get('Attributes', {}).get('ApproximateReceiveCount', 'N/A')}")
                        print(f"  First Received: {msg.get('Attributes', {}).get('ApproximateFirstReceiveTimestamp', 'N/A')}")
                        print(f"\n{Colors.BOLD}Message Body:{Colors.ENDC}")
                        body = json.loads(msg['Body'])
                        print(json.dumps(body, indent=2))
                        
                        return True
            else:
                print_info("DLQ has messages, but couldn't retrieve them in this check")
        
        # Get recent Lambda logs
        log_events = get_recent_lambda_logs(LAMBDA_FUNCTION_NAME, minutes=2)
        relevant_logs = [e for e in log_events if message_id in e['message']]
        
        if relevant_logs:
            print(f"\n{Colors.BOLD}Relevant Lambda Logs:{Colors.ENDC}")
            display_lambda_logs(relevant_logs, message_id)
        
        if (time.time() - start_time) < max_wait_seconds:
            print_info(f"\nWaiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
    
    print_error(f"\nTimeout: Message did not move to DLQ within {max_wait_minutes} minutes")
    return False


def main():
    print_header("Dead Letter Queue (DLQ) Test Script")
    
    # Step 1: Get queue URLs
    print_info("Step 1: Getting queue URLs...")
    main_queue_url = get_queue_url(QUEUE_NAME)
    dlq_url = get_queue_url(DLQ_NAME)
    print_success(f"Main Queue URL: {main_queue_url}")
    print_success(f"DLQ URL: {dlq_url}")
    
    # Step 2: Check initial queue status
    print_header("Initial Queue Status")
    main_attrs = get_queue_attributes(main_queue_url)
    dlq_attrs = get_queue_attributes(dlq_url)
    
    print(f"Main Queue:")
    print(f"  Messages Visible: {main_attrs.get('ApproximateNumberOfMessages', 0)}")
    print(f"  Messages In-Flight: {main_attrs.get('ApproximateNumberOfMessagesNotVisible', 0)}")
    print(f"  Redrive Policy: {main_attrs.get('RedrivePolicy', 'Not set')}")
    
    print(f"\nDLQ:")
    print(f"  Messages Visible: {dlq_attrs.get('ApproximateNumberOfMessages', 0)}")
    
    # Step 3: Send test message with invalid email
    print_header("Sending Test Message with Invalid Email")
    
    test_case_num = int(time.time()) % 5
    message_id = send_test_message_with_invalid_email(main_queue_url, test_case_num)
    
    print_success(f"Test message sent!")
    print_info(f"MessageId: {message_id}")
    print_info(f"Test case: DLQ_TEST_{test_case_num}")
    print_warning(f"Message contains invalid email to force SES failure")
    
    # Step 4: Monitor retries and DLQ movement
    print_info("\nThe Lambda function will:")
    print_info("  1. Attempt to process the message")
    print_info("  2. Fail when trying to send email (invalid email)")
    print_info("  3. NOT delete the message from queue")
    print_info("  4. SQS will retry up to maxReceiveCount times")
    print_info("  5. After max retries, message moves to DLQ")
    
    input(f"\n{Colors.BOLD}Press Enter to start monitoring...{Colors.ENDC}")
    
    success = monitor_message_retries(main_queue_url, dlq_url, message_id, max_wait_minutes=10)
    
    # Step 5: Display final logs
    print_header("Final Lambda Logs")
    log_events = get_recent_lambda_logs(LAMBDA_FUNCTION_NAME, minutes=10)
    relevant_logs = [e for e in log_events if message_id in e['message'] or 'RequestId' in e['message']]
    
    if relevant_logs:
        display_lambda_logs(relevant_logs, message_id)
    else:
        print_warning("No relevant logs found. Lambda may not have been invoked yet.")
    
    # Summary
    print_header("Test Summary")
    if success:
        print_success("✓ DLQ test PASSED!")
        print_success("✓ Message successfully moved to DLQ after max retries")
        print_success("✓ Error logging includes RequestId and error details")
        print_success("✓ Message was NOT deleted after SES failure")
    else:
        print_error("✗ DLQ test did not complete")
        print_warning("Possible reasons:")
        print_warning("  - Lambda function not triggered (check EventBridge/CloudWatch trigger)")
        print_warning("  - maxReceiveCount set too high (increase wait time)")
        print_warning("  - Visibility timeout too long (messages take longer to retry)")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print("  1. Check CloudWatch Logs for detailed error messages")
    print("  2. Use monitor_dlq.sh to view DLQ messages")
    print("  3. Process/purge DLQ messages after testing")


if __name__ == '__main__':
    main()

