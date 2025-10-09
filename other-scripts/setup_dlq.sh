#!/bin/bash

# Dead Letter Queue (DLQ) Setup Script
# This script creates a DLQ and configures it with the main SQS queue

set -e

# Configuration
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-141507053403}"
MAIN_QUEUE_NAME="q-dining-suggestions"
DLQ_NAME="q-dining-suggestions-dlq"
MAX_RECEIVE_COUNT=3

echo "================================================"
echo "Dead Letter Queue Setup Script"
echo "================================================"
echo ""
echo "Configuration:"
echo "  Region: $REGION"
echo "  Account ID: $ACCOUNT_ID"
echo "  Main Queue: $MAIN_QUEUE_NAME"
echo "  DLQ Name: $DLQ_NAME"
echo "  Max Receive Count: $MAX_RECEIVE_COUNT"
echo ""
echo "================================================"
echo ""

# Step 1: Check if DLQ already exists
echo "Step 1: Checking if DLQ exists..."
DLQ_URL=$(aws sqs get-queue-url --queue-name "$DLQ_NAME" --region "$REGION" 2>/dev/null | jq -r '.QueueUrl' || echo "")

if [ -z "$DLQ_URL" ]; then
    echo "  ➜ DLQ does not exist. Creating..."
    
    # Create the DLQ
    DLQ_URL=$(aws sqs create-queue \
        --queue-name "$DLQ_NAME" \
        --region "$REGION" \
        --attributes '{
            "MessageRetentionPeriod": "1209600",
            "VisibilityTimeout": "300"
        }' | jq -r '.QueueUrl')
    
    echo "  ✓ DLQ created: $DLQ_URL"
else
    echo "  ✓ DLQ already exists: $DLQ_URL"
fi

# Get DLQ ARN
DLQ_ARN=$(aws sqs get-queue-attributes \
    --queue-url "$DLQ_URL" \
    --attribute-names QueueArn \
    --region "$REGION" | jq -r '.Attributes.QueueArn')

echo "  ✓ DLQ ARN: $DLQ_ARN"
echo ""

# Step 2: Get main queue URL
echo "Step 2: Getting main queue URL..."
MAIN_QUEUE_URL=$(aws sqs get-queue-url \
    --queue-name "$MAIN_QUEUE_NAME" \
    --region "$REGION" | jq -r '.QueueUrl')

if [ -z "$MAIN_QUEUE_URL" ]; then
    echo "  ✗ Error: Main queue '$MAIN_QUEUE_NAME' not found!"
    echo "  Please create the main queue first."
    exit 1
fi

echo "  ✓ Main queue URL: $MAIN_QUEUE_URL"
echo ""

# Step 3: Configure Redrive Policy on main queue
echo "Step 3: Configuring Redrive Policy on main queue..."

REDRIVE_POLICY=$(cat <<EOF
{
  "deadLetterTargetArn": "$DLQ_ARN",
  "maxReceiveCount": $MAX_RECEIVE_COUNT
}
EOF
)

aws sqs set-queue-attributes \
    --queue-url "$MAIN_QUEUE_URL" \
    --attributes "RedrivePolicy=$REDRIVE_POLICY" \
    --region "$REGION"

echo "  ✓ Redrive Policy configured successfully!"
echo ""

# Step 4: Verify configuration
echo "Step 4: Verifying configuration..."

QUEUE_ATTRIBUTES=$(aws sqs get-queue-attributes \
    --queue-url "$MAIN_QUEUE_URL" \
    --attribute-names All \
    --region "$REGION")

CURRENT_REDRIVE_POLICY=$(echo "$QUEUE_ATTRIBUTES" | jq -r '.Attributes.RedrivePolicy')

echo "  ✓ Current Redrive Policy:"
echo "$CURRENT_REDRIVE_POLICY" | jq .
echo ""

# Step 5: Set up CloudWatch Alarms (optional but recommended)
echo "Step 5: Setting up CloudWatch Alarm for DLQ..."

ALARM_NAME="DLQ-Messages-${DLQ_NAME}"

aws cloudwatch put-metric-alarm \
    --alarm-name "$ALARM_NAME" \
    --alarm-description "Alert when messages are in the DLQ" \
    --namespace "AWS/SQS" \
    --metric-name "ApproximateNumberOfMessagesVisible" \
    --dimensions "Name=QueueName,Value=$DLQ_NAME" \
    --statistic "Average" \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold" \
    --region "$REGION" 2>/dev/null || echo "  ⚠ CloudWatch alarm creation skipped (may require SNS topic)"

echo "  ✓ CloudWatch alarm configured (if SNS topic exists)"
echo ""

# Summary
echo "================================================"
echo "✓ DLQ Setup Complete!"
echo "================================================"
echo ""
echo "Summary:"
echo "  Main Queue: $MAIN_QUEUE_URL"
echo "  DLQ: $DLQ_URL"
echo "  DLQ ARN: $DLQ_ARN"
echo "  Max Receive Count: $MAX_RECEIVE_COUNT"
echo ""
echo "What happens now:"
echo "  1. Messages that fail processing will be retried up to $MAX_RECEIVE_COUNT times"
echo "  2. After $MAX_RECEIVE_COUNT failures, messages move to DLQ"
echo "  3. Messages in DLQ are retained for 14 days"
echo "  4. You can monitor DLQ using: ./monitor_dlq.sh"
echo ""
echo "Next steps:"
echo "  1. Deploy updated Lambda function: ./deploy_lambda_updates.sh"
echo "  2. Test DLQ functionality: python test_dlq.py"
echo "  3. Monitor DLQ: ./monitor_dlq.sh"
echo ""
echo "================================================"

