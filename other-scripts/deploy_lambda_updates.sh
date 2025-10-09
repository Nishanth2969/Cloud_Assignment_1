#!/bin/bash
# Deploy Lambda Function Updates to AWS
# This script packages and deploys the updated Lambda functions

set -e  # Exit on error

echo "=========================================="
echo "Lambda Function Deployment Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    echo "Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

echo -e "${GREEN}AWS CLI found!${NC}"
echo ""

# Function to deploy a Lambda function
deploy_lambda() {
    local function_name=$1
    local source_dir=$2
    local description=$3
    
    echo "----------------------------------------"
    echo -e "${YELLOW}Deploying: ${function_name}${NC}"
    echo "Description: ${description}"
    echo "----------------------------------------"
    
    # Create temporary directory
    temp_dir=$(mktemp -d)
    echo "Creating package in: ${temp_dir}"
    
    # Copy Lambda function code
    cp -r ${source_dir}/* ${temp_dir}/
    
    # Remove test files and __pycache__
    rm -rf ${temp_dir}/tests
    rm -rf ${temp_dir}/__pycache__
    rm -rf ${temp_dir}/.pytest_cache
    
    # Create deployment package
    cd ${temp_dir}
    zip -r function.zip . > /dev/null
    
    echo "Package created: $(du -h function.zip | cut -f1)"
    
    # Deploy to AWS
    echo "Uploading to AWS Lambda..."
    aws lambda update-function-code \
        --function-name ${function_name} \
        --zip-file fileb://function.zip \
        --region us-east-1 > /dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully deployed ${function_name}${NC}"
        
        # Wait for function to be updated
        echo "Waiting for function to be ready..."
        aws lambda wait function-updated \
            --function-name ${function_name} \
            --region us-east-1
        
        echo -e "${GREEN}✓ Function is ready${NC}"
    else
        echo -e "${RED}✗ Failed to deploy ${function_name}${NC}"
        cd -
        rm -rf ${temp_dir}
        return 1
    fi
    
    # Clean up
    cd -
    rm -rf ${temp_dir}
    echo ""
}

# Main deployment flow
main() {
    echo "This script will deploy the following Lambda functions:"
    echo "1. lf1-lex-hook (Updated with new intents)"
    echo ""
    
    read -p "Do you want to proceed? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    echo ""
    echo "Starting deployment..."
    echo ""
    
    # Deploy LF1 - Lex Hook
    deploy_lambda \
        "lf1-lex-hook" \
        "../lambda-functions/lf1_lex_hook" \
        "Lex fulfillment hook with enhanced intents"
    
    echo "=========================================="
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Add new intents to Amazon Lex (see LEX_INTENTS_SETUP_GUIDE.md)"
    echo "2. Build your Lex bot"
    echo "3. Test the new intents in the Lex console"
    echo "4. Test end-to-end from your frontend"
    echo ""
    echo "To view logs:"
    echo "  aws logs tail /aws/lambda/lf1-lex-hook --follow"
    echo ""
}

# Run main function
main


