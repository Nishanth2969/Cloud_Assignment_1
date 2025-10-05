# 🍽️ Dining Concierge Chatbot

Hey there! 👋 Welcome to our AI-powered dining concierge that helps you discover the best restaurants in Manhattan. Just tell us what you're craving, and we'll send you personalized recommendations straight to your inbox!

## 🎯 What Does This Do?

Imagine having a personal restaurant concierge available 24/7. That's exactly what this chatbot does! 

- 💬 **Chat naturally** - Just ask for what you want (e.g., "I'm looking for Italian food")
- 🤖 **Smart understanding** - Powered by Amazon Lex, it actually understands what you mean
- 📧 **Email recommendations** - Get a beautiful email with handpicked restaurant suggestions
- ⚡ **Lightning fast** - All serverless, so it scales automatically

## 🏗️ How It Works

Think of it like a relay race, but for finding you the perfect dinner spot:

1. **You chat** → Our sleek React frontend sends your message
2. **API Gateway catches it** → Routes it to the right place
3. **Lambda Function (LF0)** → Talks to Amazon Lex for you
4. **Amazon Lex** → Understands what you want (the AI magic ✨)
5. **Lambda Function (LF1)** → Validates your preferences and queues your request
6. **Queue (SQS)** → Holds your request safely
7. **Lambda Function (LF2)** → Searches for restaurants and emails you the results
8. **Your inbox** → 📬 Boom! Restaurant recommendations delivered!

## 📁 Project Layout

```
dining-concierge/
├── 🎨 frontend/                     # The pretty UI (React + Vite)
├── ⚡ lambda-functions/              # The brains of the operation
│   ├── lf0_chat_proxy/             # Handles incoming chats
│   ├── lf1_lex_hook/               # Processes your preferences
│   └── lf2_suggestions_worker/     # Finds & emails restaurants
├── 🛠️ other-scripts/                # Helpful utilities
│   ├── swagger/                    # API documentation
│   ├── yelp_scraper.py             # Fetches restaurant data
│   ├── ddb_batch_write.py          # Loads data into database
│   └── os_loader.py                # Indexes restaurants for search
└── 📊 data/                         # Restaurant data lives here
```

## 🚀 Getting Started

### Running the Frontend Locally

```bash
# Jump into the frontend folder
cd frontend

# Install the goodies
npm install

# Copy the environment example and add your API URL
cp .env.example .env
# Edit .env and set your API Gateway URL

# Fire it up! 🔥
npm run dev

# Open http://localhost:5173 and start chatting!
```

### Testing the Lambda Functions

Want to make sure everything works? Run the tests!

```bash
# Activate your Python environment
source test_env/bin/activate

# Test a specific Lambda function
cd lambda-functions/lf1_lex_hook
python -m pytest tests/ -v

# Or test everything at once
cd ../..
python -m pytest tests/ -v

# All 61 tests should pass! ✅
```

### Setting Up the Data Pipeline

Need to populate the database with restaurants?

```bash
# 1. First, scrape restaurant data from Yelp
export YELP_API_KEY='your_yelp_api_key_here'
python other-scripts/yelp_scraper.py

# 2. Load data into DynamoDB
export DYNAMODB_TABLE_NAME='yelp-restaurants'
python other-scripts/ddb_batch_write.py

# 3. Index restaurants in OpenSearch for fast searching
export OPENSEARCH_ENDPOINT='your-opensearch-endpoint'
python other-scripts/os_loader.py
```

## 🧪 Testing

We take testing seriously! Here's what we've got:

- ✅ **61 unit tests** covering all Lambda functions
- ✅ **Integration tests** for end-to-end flows
- ✅ **100% passing** (because we're thorough like that)

```bash
# Run all tests with coverage
pytest tests/ -v --cov=lambda-functions

# Run specific test suites
pytest lambda-functions/lf0_chat_proxy/tests/ -v
pytest lambda-functions/lf1_lex_hook/tests/ -v
pytest lambda-functions/lf2_suggestions_worker/tests/ -v
```

## 🔧 Environment Variables

### Frontend (.env)
```bash
VITE_API_BASE_URL=https://your-api-gateway-url.amazonaws.com/dev
```

### Lambda Functions (set in AWS)
```bash
# LF0
LEX_BOT_ID=your-lex-bot-id
LEX_BOT_ALIAS_ID=your-bot-alias
LEX_LOCALE_ID=en_US

# LF1
SQS_QUEUE_URL=your-sqs-queue-url

# LF2
SQS_QUEUE_URL=your-sqs-queue-url
DYNAMODB_TABLE_NAME=yelp-restaurants
OPENSEARCH_ENDPOINT=your-opensearch-endpoint
OPENSEARCH_INDEX=restaurants
SES_SENDER_EMAIL=noreply@yourdomain.com
```

## 📚 Documentation

- 📖 **[SUBMISSION.md](SUBMISSION.md)** - Full project documentation with architecture details
- 📋 **[API Spec](other-scripts/swagger/swagger.yaml)** - Complete API documentation
- 🧪 **Test Files** - Check the `tests/` directories for examples

## 🤝 Contributing

Found a bug? Want to add a feature? Here's how:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the tests (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 🎓 Tech Stack

**Frontend:** React, Vite, React Icons  
**Backend:** AWS Lambda (Python 3.9), Amazon Lex, API Gateway  
**Data:** DynamoDB, OpenSearch, SQS  
**Communication:** AWS SES  
**Testing:** Pytest, Moto (AWS mocking)  
**CI/CD:** GitHub Actions

## 💡 Pro Tips

- **Local Development**: Use the Moto library to mock AWS services locally
- **Debugging**: Check CloudWatch Logs for Lambda function outputs
- **Cost Optimization**: Everything is serverless, so you only pay for what you use!
- **Scaling**: The system auto-scales. No servers to manage! 🎉

## 📝 License

This project is part of a cloud computing assignment. Feel free to use it for learning!

## 🆘 Need Help?

- Check the [SUBMISSION.md](SUBMISSION.md) for detailed architecture
- Look at the test files for usage examples
- Read the inline code comments
- Check AWS CloudWatch Logs for debugging

---

**Built with ❤️ and ☕ for discovering great food in Manhattan!**

*Happy dining! 🍕🍜🍣🌮🍝*
