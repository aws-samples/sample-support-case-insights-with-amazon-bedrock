import json
import logging
import os
from typing import Dict, List

import boto3

from common.utils import read_s3_json, send_sqs_message

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def process_account_list(bucket: str, key: str, queue_url: str) -> int:
    """
    Process the account list and send messages to SQS.
    
    Args:
        bucket: The S3 bucket name.
        key: The S3 object key.
        queue_url: The SQS queue URL.
        
    Returns:
        The number of accounts processed.
    """
    # Read the account list from S3
    data = read_s3_json(bucket, key)
    accounts = data.get('accounts', [])
    
    logger.info(f"Processing {len(accounts)} accounts from {bucket}/{key}")
    
    # Send a message for each account
    for account in accounts:
        account_id = account['accountId']
        
        # Create the message
        message = {
            'accountId': account_id,
            'accountName': account.get('accountName', '')
        }
        
        # Send the message to SQS
        message_id = send_sqs_message(queue_url, message)
        logger.info(f"Sent message for account {account_id} to SQS, message ID: {message_id}")
    
    return len(accounts)

def lambda_handler(event, context):
    """
    Lambda function handler for AccountReader.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict.
    """
    try:
        # Get parameters from environment variables
        queue_url = os.environ['ACTIVE_ACCOUNTS_QUEUE_URL']
        
        # Process S3 event
        for record in event['Records']:
            if record['eventSource'] == 'aws:s3' and record['eventName'].startswith('ObjectCreated'):
                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                
                logger.info(f"Processing S3 event for {bucket}/{key}")
                
                # Process the account list
                account_count = process_account_list(bucket, key, queue_url)
                
                logger.info(f"Successfully processed {account_count} accounts")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': "Successfully processed account list"
            })
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise