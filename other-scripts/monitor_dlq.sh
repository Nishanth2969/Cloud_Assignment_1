#!/bin/bash

# Dead Letter Queue (DLQ) Monitoring Script
# This script monitors the DLQ and displays messages that failed processing

set -e

# Configuration
REGION="${AWS_REGION:-us-east-1}"
DLQ_NAME="q-dining-suggestions-dlq"
MAIN_QUEUE_NAME="q-dining-suggestions"
LAMBDA_FUNCTION_NAME="lf2-suggestions-worker"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${MAGENTA}${BOLD}============================================================${NC}"
    echo -e "${MAGENTA}${BOLD}$1${NC}"
    echo -e "${MAGENTA}${BOLD}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# Get queue URL
get_queue_url() {
    aws sqs get-queue-url \
        --queue-name "$1" \
        --region "$REGION" \
        --output text 2>/dev/null || echo ""
}

# Get queue attributes
get_queue_attributes() {
    aws sqs get-queue-attributes \
        --queue-url "$1" \
        --attribute-names All \
        --region "$REGION" \
        --output json 2>/dev/null || echo "{}"
}

# Get messages from queue
get_messages() {
    aws sqs receive-message \
        --queue-url "$1" \
        --max-number-of-messages 10 \
        --attribute-names All \
        --message-attribute-names All \
        --region "$REGION" \
        --output json 2>/dev/null || echo "{}"
}

# Get recent Lambda logs
get_lambda_logs() {
    aws logs tail "/aws/lambda/$LAMBDA_FUNCTION_NAME" \
        --since "10m" \
        --format short \
        --region "$REGION" 2>/dev/null || echo ""
}

# Main script
print_header "Dead Letter Queue (DLQ) Monitor"

echo -e "${BOLD}Configuration:${NC}"
echo "  Region: $REGION"
echo "  Main Queue: $MAIN_QUEUE_NAME"
echo "  DLQ: $DLQ_NAME"
echo "  Lambda: $LAMBDA_FUNCTION_NAME"
echo ""

# Get queue URLs
print_info "Getting queue URLs..."
MAIN_QUEUE_URL=$(get_queue_url "$MAIN_QUEUE_NAME")
DLQ_URL=$(get_queue_url "$DLQ_NAME")

if [ -z "$MAIN_QUEUE_URL" ]; then
    print_error "Could not find main queue: $MAIN_QUEUE_NAME"
    exit 1
fi

if [ -z "$DLQ_URL" ]; then
    print_error "Could not find DLQ: $DLQ_NAME"
    print_warning "DLQ may not be set up. Run: ./setup_dlq.sh"
    exit 1
fi

print_success "Main Queue: $MAIN_QUEUE_URL"
print_success "DLQ: $DLQ_URL"

# Get queue statistics
print_header "Queue Statistics"

MAIN_ATTRS=$(get_queue_attributes "$MAIN_QUEUE_URL")
DLQ_ATTRS=$(get_queue_attributes "$DLQ_URL")

MAIN_VISIBLE=$(echo "$MAIN_ATTRS" | jq -r '.Attributes.ApproximateNumberOfMessages // "0"')
MAIN_IN_FLIGHT=$(echo "$MAIN_ATTRS" | jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"')
MAIN_DELAYED=$(echo "$MAIN_ATTRS" | jq -r '.Attributes.ApproximateNumberOfMessagesDelayed // "0"')

DLQ_VISIBLE=$(echo "$DLQ_ATTRS" | jq -r '.Attributes.ApproximateNumberOfMessages // "0"')
DLQ_IN_FLIGHT=$(echo "$DLQ_ATTRS" | jq -r '.Attributes.ApproximateNumberOfMessagesNotVisible // "0"')

echo -e "${BOLD}Main Queue ($MAIN_QUEUE_NAME):${NC}"
echo "  Messages Visible: $MAIN_VISIBLE"
echo "  Messages In-Flight: $MAIN_IN_FLIGHT"
echo "  Messages Delayed: $MAIN_DELAYED"
echo ""

echo -e "${BOLD}Dead Letter Queue ($DLQ_NAME):${NC}"
echo "  Messages Visible: $DLQ_VISIBLE"
echo "  Messages In-Flight: $DLQ_IN_FLIGHT"
echo ""

# Check Redrive Policy
REDRIVE_POLICY=$(echo "$MAIN_ATTRS" | jq -r '.Attributes.RedrivePolicy // "Not configured"')
if [ "$REDRIVE_POLICY" != "Not configured" ]; then
    print_success "Redrive Policy configured:"
    echo "$REDRIVE_POLICY" | jq .
else
    print_warning "Redrive Policy not configured!"
    print_warning "Run ./setup_dlq.sh to configure DLQ"
fi

echo ""

# Check DLQ messages
if [ "$DLQ_VISIBLE" -gt 0 ]; then
    print_header "DLQ Messages (Failed Requests)"
    
    print_warning "Found $DLQ_VISIBLE message(s) in DLQ"
    print_info "These messages failed after maximum retry attempts"
    echo ""
    
    # Retrieve messages (without deleting)
    MESSAGES=$(get_messages "$DLQ_URL")
    MESSAGE_COUNT=$(echo "$MESSAGES" | jq -r '.Messages | length')
    
    if [ "$MESSAGE_COUNT" -gt 0 ]; then
        echo "$MESSAGES" | jq -r '.Messages[] | 
            "----------------------------------------\n" +
            "MessageId: " + .MessageId + "\n" +
            "Receive Count: " + (.Attributes.ApproximateReceiveCount // "N/A") + "\n" +
            "First Received: " + (.Attributes.ApproximateFirstReceiveTimestamp // "N/A") + "\n" +
            "Message Body:\n" + .Body + "\n"'
        
        echo ""
        print_info "To process or delete DLQ messages, use:"
        echo "  - Reprocess: aws sqs send-message --queue-url $MAIN_QUEUE_URL --message-body '...'"
        echo "  - Delete: aws sqs purge-queue --queue-url $DLQ_URL"
    else
        print_info "Could not retrieve DLQ messages (they may be in-flight)"
    fi
else
    print_success "No messages in DLQ - all processing successful!"
fi

# Get recent Lambda error logs
print_header "Recent Lambda Error Logs"

print_info "Fetching logs from last 10 minutes..."
echo ""

LOGS=$(get_lambda_logs | grep -E "(ERROR|FAILED|RequestId|MessageId|SES send_email)" || true)

if [ -n "$LOGS" ]; then
    echo "$LOGS"
else
    print_success "No error logs found in the last 10 minutes"
fi

# Summary
print_header "Summary"

if [ "$DLQ_VISIBLE" -gt 0 ]; then
    print_warning "Action Required: $DLQ_VISIBLE message(s) in DLQ need attention"
    echo ""
    echo "Common reasons for DLQ messages:"
    echo "  1. Invalid email addresses (SES rejection)"
    echo "  2. SES sending limits exceeded"
    echo "  3. DynamoDB/OpenSearch failures"
    echo "  4. Lambda timeout or out-of-memory errors"
    echo ""
    echo "Next steps:"
    echo "  1. Review the message details above"
    echo "  2. Check CloudWatch Logs for full error context"
    echo "  3. Fix the underlying issue (e.g., correct email address)"
    echo "  4. Optionally reprocess the message or delete it"
else
    print_success "System healthy - no failed messages"
fi

echo ""
print_info "To continuously monitor, run: watch -n 30 ./monitor_dlq.sh"
echo ""

