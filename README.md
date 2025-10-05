# Infrastructure Resources

## DynamoDB
- **Table Name:** yelp-restaurants
- **Partition Key:** business_id (string)
- **Billing Mode:** On-demand
- **ARN:** arn:aws:dynamodb:us-east-1:141507053403:table/yelp-restaurants

## SQS
- **Queue Name:** q-dining-suggestions
- **Type:** Standard
- **URL:** https://sqs.us-east-1.amazonaws.com/141507053403/q-dining-suggestions
- **ARN:** arn:aws:sqs:us-east-1:141507053403:q-dining-suggestions

## S3
- **Bucket Name:** <bucket name>
- **Website URL:** <S3 website endpoint>

## API Gateway
- **API Name:** AI-Customer-Service-API
- **Stage:** dev
- **URL:** https://gtsrvcex0b.execute-api.us-east-1.amazonaws.com/dev/chatbot

## Lambda Functions
- **LF0 (Proxy):** LF0-proxy
  - ARN: arn:aws:lambda:us-east-1:141507053403:function:LF0-proxy