# Dining Concierge Chatbot

A serverless, microservice-driven web application that provides restaurant recommendations through natural language conversation. Built for Cloud Computing Assignment 1.

## Overview

This application implements a complete dining concierge chatbot that collects user preferences through conversation and delivers personalized restaurant recommendations via email. The system uses Amazon Lex for natural language understanding, AWS Lambda for serverless processing, and integrates with Yelp API for restaurant data.

## Architecture

The system follows a microservices architecture with the following components:

1. **Frontend (React)** - Modern web interface for user interaction
2. **API Gateway** - REST API endpoint management
3. **Lambda LF0 (Chat Proxy)** - Handles incoming chat requests and integrates with Lex
4. **Amazon Lex** - Natural language understanding and conversation management
5. **Lambda LF1 (Lex Hook)** - Processes user preferences and validates input
6. **SQS Queue** - Message queuing for asynchronous processing
7. **Lambda LF2 (Suggestions Worker)** - Processes requests and sends email recommendations
8. **DynamoDB** - Restaurant data storage
9. **OpenSearch** - Fast restaurant search and filtering
10. **SES** - Email delivery service
11. **Dead Letter Queue** - Error handling and retry mechanism

## Features

### Core Functionality
- Natural language conversation interface
- Restaurant recommendation system
- Email delivery of personalized suggestions
- Support for 8+ cuisine types
- Manhattan restaurant coverage
- Real-time chat experience

### Chatbot Intents
The Lex bot supports 9 conversational intents:

**Required Intents:**
- GreetingIntent - Initial greeting and introduction
- ThankYouIntent - Polite responses to thanks
- DiningSuggestionsIntent - Main recommendation flow

**Bonus Intents:**
- HelpIntent - User guidance and assistance
- CancelIntent - Cancel current requests
- ChangeMindIntent - Start over with new preferences
- RestaurantTypesIntent - Show available cuisines
- LocationIntent - Explain coverage areas
- FeedbackIntent - Collect user feedback

### Data Collection
The DiningSuggestionsIntent collects 5 required parameters:
1. Location - User's preferred dining area
2. Cuisine - Type of food desired
3. Dining Time - When they want to dine
4. Party Size - Number of people
5. Email - Where to send recommendations

## Project Structure

```
Cloud_Assignment_1/
├── frontend/                          # React frontend application
│   ├── src/
│   │   └── App.jsx                    # Main UI component
│   ├── dist/                          # Production build for S3
│   └── package.json                   # Dependencies
│
├── lambda-functions/
│   ├── lf0_chat_proxy/                # API to Lex proxy
│   │   ├── lambda_function.py         # Main handler
│   │   └── tests/ (7 tests)           # Unit tests
│   │
│   ├── lf1_lex_hook/                  # Lex intent handler
│   │   ├── lambda_function.py         # 9 intents implementation
│   │   └── tests/ (27 tests)          # Unit tests
│   │
│   └── lf2_suggestions_worker/        # Email worker with DLQ
│       ├── lambda_function.py         # Queue processor
│       └── tests/ (19 tests)          # Unit tests + DLQ tests
│
├── other-scripts/
│   ├── yelp_scraper.py                # Yelp API scraper
│   ├── ddb_batch_write.py             # DynamoDB loader
│   ├── os_loader.py                   # OpenSearch indexer
│   ├── setup_dlq.sh                   # DLQ automation
│   ├── test_dlq.py                    # DLQ testing
│   ├── monitor_dlq.sh                 # DLQ monitoring
│   └── swagger/swagger.yaml           # API specification
│
├── data/
│   └── restaurants.json               # 1000+ restaurants from Yelp
│
└── tests/
    └── test_integration.py            # Integration tests
```

## Getting Started

### Prerequisites
- Node.js 18+ for frontend development
- Python 3.9+ for Lambda functions
- AWS CLI configured with appropriate permissions
- Yelp API key for restaurant data

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env
# Edit .env and set your API Gateway URL

# Start development server
npm run dev

# Open http://localhost:5173
```

### Lambda Function Testing

```bash
# Activate Python environment
source test_env/bin/activate

# Test individual Lambda functions
cd lambda-functions/lf0_chat_proxy
python -m pytest tests/ -v

cd ../lf1_lex_hook
python -m pytest tests/ -v

cd ../lf2_suggestions_worker
python -m pytest tests/ -v

# Test all functions
cd ../..
python -m pytest lambda-functions/ -v
```

### Data Pipeline Setup

```bash
# 1. Scrape restaurant data from Yelp
export YELP_API_KEY='your_yelp_api_key'
python other-scripts/yelp_scraper.py

# 2. Load data into DynamoDB
export DYNAMODB_TABLE_NAME='yelp-restaurants'
python other-scripts/ddb_batch_write.py

# 3. Index restaurants in OpenSearch
export OPENSEARCH_ENDPOINT='your-opensearch-endpoint'
python other-scripts/os_loader.py
```

## Testing

The project includes comprehensive testing with 53 unit tests covering all components:

- **LF0 (Chat Proxy)**: 7 tests - API integration and error handling
- **LF1 (Lex Hook)**: 27 tests - Intent handling and slot validation
- **LF2 (Suggestions Worker)**: 19 tests - Email processing and DLQ functionality

All tests pass with 100% success rate.

```bash
# Run all tests
pytest lambda-functions/ -v

# Run with coverage
pytest lambda-functions/ -v --cov=lambda-functions

# Run specific test suites
pytest lambda-functions/lf0_chat_proxy/tests/ -v
pytest lambda-functions/lf1_lex_hook/tests/ -v
pytest lambda-functions/lf2_suggestions_worker/tests/ -v
```

## Environment Configuration

### Frontend (.env)
```bash
VITE_API_BASE_URL=https://your-api-gateway-url.amazonaws.com/dev
```

### Lambda Functions (AWS Environment Variables)

**LF0 (Chat Proxy):**
```bash
LEX_BOT_ID=your-lex-bot-id
LEX_BOT_ALIAS_ID=your-bot-alias
LEX_LOCALE_ID=en_US
```

**LF1 (Lex Hook):**
```bash
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/account/q-dining-suggestions
```

**LF2 (Suggestions Worker):**
```bash
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/account/q-dining-suggestions
DYNAMODB_TABLE_NAME=yelp-restaurants
OPENSEARCH_ENDPOINT=your-opensearch-endpoint
OPENSEARCH_INDEX=restaurants
SES_SENDER_EMAIL=noreply@yourdomain.com
```

## Assignment Requirements Status

### Base Requirements (80 points)
1. **Frontend Application (10 pts)** - Complete
   - React frontend with modern UI
   - S3 deployment ready
   - CORS-enabled API integration

2. **API Implementation (15 pts)** - Complete
   - API Gateway with Swagger specification
   - Lambda LF0 for chat operations
   - Proper request/response handling

3. **Dining Concierge Chatbot (20 pts)** - Complete
   - Amazon Lex bot with 9 intents
   - Lambda LF1 code hook
   - Collects all 5 required parameters
   - SQS integration for request queuing

4. **Lex Integration (10 pts)** - Complete
   - AWS SDK integration in LF0
   - Complete message flow implementation

5. **Yelp API Integration (15 pts)** - Complete
   - 1000+ restaurants from 8 cuisines
   - DynamoDB storage with required fields
   - Duplicate removal and data validation

6. **OpenSearch Integration (15 pts)** - Complete
   - Restaurant index with proper mapping
   - Random sampling for recommendations
   - Fallback to DynamoDB

7. **Suggestions Module (15 pts)** - Complete
   - Lambda LF2 queue worker
   - OpenSearch and DynamoDB integration
   - SES email delivery with HTML templates

### Extra Credit (10 points)
8. **Dead Letter Queue** - Complete
   - DLQ attached to SQS queue
   - maxReceiveCount set to 3
   - Comprehensive error logging
   - Retry mechanism for failed messages

## Example Conversation Flow

```
User: Hello
Bot: Hi there! I'm your dining concierge. I can help you find amazing restaurants in Manhattan. What type of cuisine are you craving?

User: I need restaurant suggestions
Bot: Great! I can help you with that. What city or area are you looking to dine in?

User: Manhattan
Bot: Got it, Manhattan! What cuisine would you like to try?

User: Japanese
Bot: Excellent choice! What time would you like to dine?

User: 7 PM
Bot: Perfect! How many people will be dining?

User: Two
Bot: Wonderful! What's your email address?

User: user@example.com
Bot: You're all set. Expect my suggestions shortly! Have a good day.

User: Thank you!
Bot: You're very welcome! Enjoy your dining experience!
```

## Email Output

Users receive professionally formatted emails with:
- Restaurant recommendations based on preferences
- Complete restaurant details (name, address, rating, phone)
- Star rating visualization
- Clickable Yelp links
- Mobile-responsive design

## Error Handling

The system includes comprehensive error handling:
- Input validation for all user parameters
- Graceful fallback mechanisms
- Dead Letter Queue for failed email deliveries
- Detailed logging with RequestId and MessageId tracking
- User-friendly error messages

## Technology Stack

**Frontend:**
- React 18 with Vite
- Modern CSS with responsive design
- Real-time chat interface

**Backend:**
- AWS Lambda (Python 3.9)
- Amazon Lex V2 for NLP
- API Gateway for REST API
- SQS for message queuing
- DynamoDB for data storage
- OpenSearch for search functionality
- SES for email delivery

**Testing:**
- Pytest for unit testing
- Moto for AWS service mocking
- 53 comprehensive tests

**DevOps:**
- Serverless architecture
- CloudWatch for monitoring
- EventBridge for scheduling
- IAM for security

## Deployment

### Frontend Deployment
```bash
# Build for production
cd frontend
npm run build

# Deploy dist/ folder to S3 bucket with static website hosting
```

### Lambda Deployment
```bash
# Deploy Lambda functions
./other-scripts/deploy_lambda_updates.sh

# Set up DLQ
./other-scripts/setup_dlq.sh
```

## Performance Metrics

- **Test Coverage**: 100% (53/53 tests passing)
- **Response Time**: <1 second for OpenSearch queries
- **Email Delivery**: HTML + plain-text format
- **Data Volume**: 1000+ restaurants across 8 cuisines
- **Availability**: Serverless auto-scaling architecture

## Security Features

- HTTPS everywhere
- IAM role-based access control
- API Gateway authentication
- Input validation and sanitization
- AWS4Auth for OpenSearch
- Environment variable management
- CORS properly configured

## Monitoring and Logging

- CloudWatch Logs integration
- RequestId and MessageId tracking
- Error type classification
- DLQ monitoring scripts
- Performance metrics collection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Commit your changes
6. Push to the branch
7. Open a Pull Request

## License

This project is part of a Cloud Computing assignment. Use for educational purposes.

## Support

For questions or issues:
- Check CloudWatch Logs for debugging
- Review test files for usage examples
- Read inline code comments
- Consult AWS documentation for service-specific issues

---

**Built for Cloud Computing Assignment 1 - Fall 2025**

