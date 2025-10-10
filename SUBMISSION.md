# Dining Concierge - Assignment Submission

## Project Overview

A serverless dining concierge chatbot that helps users find restaurant recommendations in Manhattan using AWS services.

## Architecture

The application follows a serverless microservices architecture implementing a Dining Concierge chatbot:

1. **Frontend**: React application hosted on S3 bucket with static website hosting
2. **API Gateway**: RESTful API with Swagger specification and CORS enabled
3. **Lambda Functions**: Three core functions for different responsibilities
4. **Amazon Lex**: Natural language processing chatbot with three intents
5. **DynamoDB**: Restaurant data storage with full restaurant details
6. **ElasticSearch**: Restaurant search and filtering service
7. **SQS**: Asynchronous message processing with Dead Letter Queue
8. **SES**: Email delivery service for restaurant recommendations
9. **EventBridge**: Scheduled triggers for automated queue processing
10. **CloudWatch**: Monitoring and logging for all services

## AWS Resources

### Frontend & API
- **S3 Bucket**: [TO BE FILLED BY YOGA]
- **CloudFront Distribution**: [TO BE FILLED BY YOGA]
- **API Gateway**: [TO BE FILLED BY YOGA]
  - Stage: dev
  - Endpoint: [TO BE FILLED BY YOGA]

### Lambda Functions
- **LF0 (Chat Proxy)**: [TO BE FILLED BY YOGA]
  - Runtime: Python 3.9
  - Purpose: API Gateway integration, proxy requests to Amazon Lex using AWS SDK
  - Function: Extract text from API request, send to Lex, return response
- **LF1 (Lex Hook)**: [TO BE FILLED BY YOGA]
  - Runtime: Python 3.9
  - Purpose: Lex code hook for intent processing and validation
  - Function: Handle GreetingIntent, ThankYouIntent, DiningSuggestionsIntent, push to SQS
- **LF2 (Suggestions Worker)**: [TO BE FILLED BY YOGA]
  - Runtime: Python 3.9
  - Purpose: Queue worker for processing restaurant suggestions
  - Function: Pull from SQS, query ElasticSearch, fetch from DynamoDB, send email via SES

### Data Services
- **DynamoDB Table**: [TO BE FILLED BY YOGA]
  - Table Name: yelp-restaurants
  - Primary Key: business_id
  - Capacity: On-demand
  - Required Fields: Business ID, Name, Address, Coordinates, Number of Reviews, Rating, Zip Code, insertedAtTimestamp
- **ElasticSearch Domain**: [TO BE FILLED BY YOGA]
  - Index: restaurants
  - Document Type: Restaurant
  - Stored Fields: RestaurantID, Cuisine
- **SQS Queue**: [TO BE FILLED BY YOGA]
  - Queue Name: q-dining-suggestions
  - Visibility Timeout: 300 seconds
- **Dead Letter Queue (DLQ)**: [TO BE FILLED BY YOGA]
  - Queue Name: q-dining-suggestions-dlq
  - Max Receive Count: 3-5
  - Purpose: Handle failed email delivery attempts

### AI & Communication
- **Amazon Lex Bot**: [TO BE FILLED BY YOGA]
  - Bot Name: DiningConciergeBot
  - Locale: en_US
  - Intents: GreetingIntent, ThankYouIntent, DiningSuggestionsIntent
- **SES Configuration**: [TO BE FILLED BY YOGA]
  - Sender Email: [TO BE FILLED BY YOGA]
  - Region: us-east-1

### Scheduling & Monitoring
- **EventBridge Scheduler**: [TO BE FILLED BY YOGA]
  - Schedule: rate(1 minute)
  - Target: LF2 Lambda function
  - Purpose: Automated queue worker polling
- **CloudWatch Logs**: [TO BE FILLED BY YOGA]
  - Log Groups for each Lambda function
  - DLQ failure logging with requestId and error reasons

## Data Pipeline

### Restaurant Data Collection
- **Source**: Yelp Fusion API
- **Cuisines**: Minimum 5 cuisine types (Italian, Chinese, Japanese, Mexican, Indian, American, French, Thai)
- **Target**: 200+ restaurants per cuisine, 1000+ total restaurants
- **Location**: Manhattan, NY
- **Search Method**: Cuisine-specific search terms (e.g., "Chinese restaurants")
- **Deduplication**: Ensures no duplicate restaurants across cuisines

### Data Storage
1. **DynamoDB**: Full restaurant details including:
   - Business ID (Primary Key), Name, Address, Coordinates
   - Rating, Review Count, Phone, Categories, Zip Code
   - Price Range, Yelp URL, Image URL
   - insertedAtTimestamp (required field)

2. **ElasticSearch**: Indexed data for search:
   - RestaurantID
   - Cuisine type
   - Optimized for random selection queries by cuisine

## Application Flow

1. **User Interaction**: User sends message via frontend
2. **API Processing**: API Gateway routes to LF0 (Chat Proxy)
3. **Lex Integration**: LF0 forwards message to Amazon Lex using AWS SDK
4. **Intent Processing**: Lex calls LF1 (Lex Hook) for intent handling
5. **Data Collection**: LF1 validates and collects required slots (Location, Cuisine, Dining Time, Number of people, Email)
6. **Queue Processing**: Complete requests sent to SQS queue (Q1)
7. **Confirmation**: User receives confirmation that suggestions will be sent via email
8. **Automated Processing**: EventBridge Scheduler triggers LF2 every minute
9. **Recommendation Engine**: LF2 processes SQS messages
10. **Search & Retrieval**: Query ElasticSearch for random restaurants by cuisine, fetch details from DynamoDB
11. **Email Delivery**: Format and send recommendations via SES
12. **Error Handling**: Failed emails retry via SQS, then move to DLQ after max attempts

## Key Features

### Conversation Management
- **GreetingIntent**: Welcome users and explain capabilities (e.g., "Hi there, how can I help?")
- **ThankYouIntent**: Acknowledge gratitude and encourage future use (e.g., "You're welcome.")
- **DiningSuggestionsIntent**: Collect dining preferences through conversation

### Required User Input Collection
The DiningSuggestionsIntent collects the following information through conversation:
- **Location**: City or city area (validated for Manhattan)
- **Cuisine**: Cuisine type preference
- **Dining Time**: Date and time for dining
- **Number of people**: Party size (1-20 people)
- **Email**: Email address for receiving recommendations

### Input Validation
- **Location**: Must be in Manhattan area
- **Cuisine**: Validated against supported cuisine types
- **Party Size**: 1-20 people
- **Dining Time**: Future time validation
- **Email**: Valid email format required

### Recommendation System
- **Search Strategy**: Random selection from cuisine-filtered results in ElasticSearch
- **Data Retrieval**: Fetch detailed restaurant information from DynamoDB using restaurant IDs
- **Email Format**: Formatted email with restaurant name and address for each recommendation
- **Fallback Logic**: DynamoDB scan if ElasticSearch unavailable

## Testing

### Unit Tests
- **LF1**: Intent handling, slot validation, SQS integration
- **LF2**: Message processing, email formatting, error handling
- **Coverage**: Core business logic and edge cases

### Integration Testing
- **End-to-End Flow**: Frontend → API → Lex → SQS → Email
- **Error Scenarios**: Invalid inputs, service failures, timeouts
- **Performance**: Message processing under load

## Deployment

### CI/CD Pipeline
- **GitHub Actions**: Automated testing and linting
- **Frontend**: Node.js testing and build
- **Backend**: Python linting and unit tests

### Environment Configuration
- **Development**: Local testing with mock services
- **Production**: AWS services with proper IAM roles

## Security

### IAM Roles & Policies
- **Principle of Least Privilege**: Each Lambda has minimal required permissions
- **Service-to-Service**: Secure communication between AWS services
- **API Security**: CORS configuration and input validation

### Data Protection
- **Email Privacy**: No storage of user email addresses
- **Request Logging**: Structured logging without sensitive data
- **Error Handling**: Generic error messages to users

## Monitoring & Observability

### CloudWatch Integration
- **Metrics**: Lambda invocations, errors, duration
- **Logs**: Structured logging for debugging
- **Alarms**: Dead letter queue monitoring
- **DLQ Monitoring**: Failed email attempts logged with requestId and error reasons

### Performance Metrics
- **Response Time**: API Gateway to email delivery
- **Success Rate**: End-to-end completion percentage
- **Error Tracking**: Categorized error types and frequencies

## Example Interaction Flow

### User Conversation Example
```
User: Hello
Bot: Hi there, how can I help?

User: I need some restaurant suggestions.
Bot: Great. I can help you with that. What city or city area are you looking to dine in?

User: Manhattan
Bot: Got it, Manhattan. What cuisine would you like to try?

User: Japanese
Bot: Ok, how many people are in your party?

User: Two
Bot: A few more to go. What date?

User: Today
Bot: What time?

User: 7 pm, please
Bot: Great. Lastly, I need your email so I can send you my findings.

User: user@example.com
Bot: You're all set. Expect my suggestions shortly! Have a good day.

User: Thank you!
Bot: You're welcome.
```

### Email Delivery Example
```
Hello! Here are my Japanese restaurant suggestions for 2 people, for today at 7 pm:

1. Sushi Nakazawa, located at 23 Commerce St
2. Jin Ramen, located at 3183 Broadway
3. Nikko, located at 1280 Amsterdam Ave.

Enjoy your meal!
```

## Future Enhancements

### Scalability
- **Auto Scaling**: Lambda concurrency limits
- **Caching**: Restaurant data caching for improved performance
- **CDN**: Global content delivery for frontend

### Features
- **Personalization**: User preference learning
- **Real-time Availability**: Restaurant booking integration
- **Multi-language**: Support for additional languages

## Repository Structure

```
├── frontend/                 # React frontend application
├── lambda-functions/         # AWS Lambda function code
│   ├── lf0_chat_proxy/      # Chat API proxy (LF0)
│   ├── lf1_lex_hook/        # Lex intent handler (LF1)
│   └── lf2_suggestions_worker/ # Queue worker (LF2)
├── other-scripts/           # Utility scripts
│   ├── swagger/             # API specification
│   ├── yelp_scraper.py      # Restaurant data scraper
│   ├── ddb_batch_write.py   # DynamoDB data loader
│   ├── os_loader.py         # ElasticSearch data loader
│   └── release.sh           # Release packaging script
└── data/                    # Generated restaurant data
```

## Assignment Requirements Compliance

### Core Requirements (100 points)
1. **Frontend Deployment (10 points)**: React app hosted on S3 with static website hosting
2. **API Implementation (15 points)**: API Gateway with Swagger spec, LF0 Lambda function, CORS enabled
3. **Lex Chatbot (20 points)**: Three intents (GreetingIntent, ThankYouIntent, DiningSuggestionsIntent), LF1 code hook
4. **Lex Integration (10 points)**: LF0 integrates with Lex using AWS SDK
5. **Yelp Data Collection (15 points)**: 1000+ restaurants from Manhattan, 5+ cuisines, DynamoDB storage
6. **ElasticSearch Setup (15 points)**: restaurants index, Restaurant type, partial data storage
7. **Suggestions Module (15 points)**: LF2 queue worker, EventBridge scheduler, SES email delivery

### Extra Credit (10 points)
- **Dead Letter Queue**: DLQ attached to SQS with maxReceiveCount 3-5
- **Error Handling**: Failed emails retry via SQS, then move to DLQ
- **Logging**: CloudWatch logs with requestId and error reasons
- **Demonstration**: Screenshot evidence of DLQ functionality

