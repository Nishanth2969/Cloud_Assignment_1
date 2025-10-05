import json
import boto3
import logging
import os
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_lex_client():
    return boto3.client('lexv2-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return cors_response(200, {'message': 'OK'})
        
        if event.get('httpMethod') != 'POST':
            return cors_response(405, {'error': 'Method not allowed'})
        
        body = json.loads(event.get('body', '{}'))
        
        if not body.get('message') or not body.get('message').strip():
            return cors_response(400, {'error': 'Message is required'})
        
        user_message = body['message'].strip()
        session_id = body.get('sessionId', 'default-session')
        
        if len(user_message) > 1000:
            return cors_response(400, {'error': 'Message too long'})
        
        lex_response = send_to_lex(user_message, session_id)
        
        if lex_response:
            return cors_response(200, lex_response)
        else:
            return cors_response(500, {'error': 'Failed to process message'})
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return cors_response(400, {'error': 'Invalid JSON'})
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return cors_response(500, {'error': 'Internal server error'})

def send_to_lex(message: str, session_id: str) -> Dict[str, Any]:
    try:
        bot_id = os.environ.get('LEX_BOT_ID')
        bot_alias_id = os.environ.get('LEX_BOT_ALIAS_ID', 'TSTALIASID')
        locale_id = os.environ.get('LEX_LOCALE_ID', 'en_US')
        
        if not bot_id:
            logger.error("LEX_BOT_ID environment variable not set")
            return None
        
        lex_client = get_lex_client()
        response = lex_client.recognize_text(
            botId=bot_id,
            botAliasId=bot_alias_id,
            localeId=locale_id,
            sessionId=session_id,
            text=message
        )
        
        logger.info(f"Lex response: {json.dumps(response, default=str)}")
        
        lex_message = ""
        if response.get('messages'):
            lex_message = response['messages'][0].get('content', '')
        
        intent_name = ""
        if response.get('sessionState', {}).get('intent'):
            intent_name = response['sessionState']['intent'].get('name', '')
        
        slots = {}
        if response.get('sessionState', {}).get('intent', {}).get('slots'):
            raw_slots = response['sessionState']['intent']['slots']
            for slot_name, slot_data in raw_slots.items():
                if slot_data and slot_data.get('value'):
                    slots[slot_name] = slot_data['value'].get('interpretedValue', '')
        
        return {
            'message': lex_message or "I'm sorry, I didn't understand that. Could you please try again?",
            'sessionId': session_id,
            'intentName': intent_name,
            'slots': slots
        }
    
    except Exception as e:
        logger.error(f"Error communicating with Lex: {str(e)}")
        return None

def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body)
    }

def health_check():
    return cors_response(200, {
        'status': 'healthy',
        'timestamp': context.aws_request_id if 'context' in globals() else 'unknown',
        'version': '1.0.0'
    })
