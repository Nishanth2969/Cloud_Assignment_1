import json
import boto3
import hashlib

lex_client = boto3.client('lexv2-runtime', region_name='us-east-1')

BOT_ID = 'UGJJGXTCJ9'
BOT_ALIAS_ID = 'TSTALIASID'
LOCALE_ID = 'en_US'


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    try:
        body = json.loads(event.get('body', '{}'))
        messages = body.get('messages', [])

        if not messages:
            raise ValueError("No messages in request")

        user_message = messages[0].get('unstructured', {}).get('text', '')

        if not user_message:
            raise ValueError("No text in message")

        print(f"User message: {user_message}")

        # Generate consistent session ID from source IP
        source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'default-ip')
        session_id = 'session-' + hashlib.md5(source_ip.encode()).hexdigest()[:16]

        print(f"Session ID: {session_id}")

        lex_response = lex_client.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId=LOCALE_ID,
            sessionId=session_id,
            text=user_message
        )

        print("Full Lex response:", json.dumps(lex_response, default=str))

        bot_messages = lex_response.get('messages', [])
        bot_message = bot_messages[0].get('content',
                                          'Sorry, I did not understand that.') if bot_messages else 'Sorry, I did not understand that.'

        print(f"Bot response: {bot_message}")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps({
                "messages": [
                    {
                        "type": "unstructured",
                        "unstructured": {
                            "text": bot_message
                        }
                    }
                ]
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "messages": [
                    {
                        "type": "unstructured",
                        "unstructured": {
                            "text": "Sorry, I'm having trouble. Please try again."
                        }
                    }
                ]
            })
        }