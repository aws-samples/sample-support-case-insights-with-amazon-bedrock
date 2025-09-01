import json
import logging
import os
from typing import Dict

import boto3

from common.utils import assume_role, send_sqs_message, write_s3_json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_case_communications(session, case_id: str) -> Dict:
    """
    Get communications for a support case.
    
    Args:
        session: The boto3 session.
        case_id: The case ID.
        
    Returns:
        The case communications.
    """
    support_client = session.client('support')
    
    communications = []
    next_token = None
    
    try:
        while True:
            # Build the request parameters
            params = {
                'caseId': case_id
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            # Call the API
            response = support_client.describe_communications(**params)
            
            # Process the communications
            for comm in response.get('communications', []):
                communications.append({
                    'body': comm.get('body', ''),
                    'timeCreated': comm.get('timeCreated', ''),
                    'submittedBy': comm.get('submittedBy', '')
                })
            
            # Check if there are more communications
            next_token = response.get('nextToken')
            if not next_token:
                break
        
        logger.info(f"Retrieved {len(communications)} communications for case {case_id}")
        return {'communications': communications}
    except Exception as e:
        logger.warning(f"Failed to retrieve communications for case {case_id}: {str(e)}")
        raise

def process_case(account_id: str, display_id: str, case_id: str, bucket_name: str, summary_queue_url: str) -> bool:
    """
    Process a support case to retrieve and store communications.
    
    Args:
        account_id: The AWS account ID.
        display_id: The case display ID.
        case_id: The case ID.
        bucket_name: The S3 bucket name.
        summary_queue_url: The SQS queue URL for case summaries.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Assume the role in the target account
        role_name = os.environ['SUPPORT_ROLE_NAME']
        session_name = f"CaseAnnotation-{display_id}"
        
        logger.info(f"Assuming role {role_name} in account {account_id}")
        session = assume_role(account_id, role_name, session_name)
        
        # Get case communications
        communications = get_case_communications(session, case_id)
        
        # Store the communications
        account_folder = f"account_number={account_id}"
        case_folder = f"{account_folder}/case_number={display_id}"
        annotation_key = f"{case_folder}/annotation.json"
        
        write_s3_json(bucket_name, annotation_key, communications)
        
        # Send a message to the summary queue
        message = {
            'filePath': f"{bucket_name}/{case_folder}"
        }
        
        send_sqs_message(summary_queue_url, message)
        
        logger.info(f"Successfully processed case {display_id} for account {account_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to process case {display_id} for account {account_id}: {str(e)}")
        return False

def lambda_handler(event, context):
    """
    Lambda function handler for CaseAnnotation.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict.
    """
    try:
        # Get parameters from environment variables
        bucket_name = os.environ['CASE_RAW_BUCKET']
        summary_queue_url = os.environ['CASE_SUMMARY_QUEUE_URL']
        
        success_count = 0
        failure_count = 0
        
        # Process SQS event
        for record in event['Records']:
            if record['eventSource'] == 'aws:sqs':
                # Parse the message
                message = json.loads(record['body'])
                account_id = message.get('accountId')
                display_id = message.get('displayId')
                case_id = message.get('caseId')
                
                if not all([account_id, display_id, case_id]):
                    logger.error("Missing required fields in SQS message")
                    failure_count += 1
                    continue
                
                logger.info(f"Processing case {display_id} for account {account_id}")
                
                # Process the case
                if process_case(account_id, display_id, case_id, bucket_name, summary_queue_url):
                    success_count += 1
                else:
                    failure_count += 1
        
        logger.info(f"Processed {success_count} cases successfully, {failure_count} failures")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Processed {success_count} cases successfully, {failure_count} failures"
            })
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise