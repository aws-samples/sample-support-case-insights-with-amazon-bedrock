import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

import boto3

from common.utils import assume_role, get_existing_cases_batch, send_sqs_message, write_s3_json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_support_cases(session, months_back: int = 12) -> List[Dict]:
    """
    Get support cases for the trailing months.
    
    Args:
        session: The boto3 session.
        months_back: The number of months to look back.
        
    Returns:
        A list of support cases.
    """
    support_client = session.client('support')
    
    # Calculate the start date (trailing months)
    start_date = (datetime.utcnow() - timedelta(days=30 * months_back)).strftime('%Y-%m-%d')
    
    cases = []
    next_token = None
    
    try:
        while True:
            # Build the request parameters
            params = {
                'includeCommunications': False,
                'includeResolvedCases': True,
                'afterTime': start_date
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            # Call the API
            response = support_client.describe_cases(**params)
            
            # Process the cases
            for case in response.get('cases', []):
                # Only process resolved cases
                status = case.get('status', '')
                if status.lower() == 'resolved':
                    cases.append({
                        'caseId': case.get('caseId', ''),
                        'displayId': case.get('displayId', ''),
                        'subject': case.get('subject', ''),
                        'serviceCode': case.get('serviceCode', ''),
                        'categoryCode': case.get('categoryCode', ''),
                        'severityCode': case.get('severityCode', ''),
                        'submittedBy': case.get('submittedBy', ''),
                        'timeCreated': case.get('timeCreated', ''),
                        'status': status,
                        'Case_Retrieval_Date': datetime.utcnow().isoformat(),
                        'Case_Summary': None,
                        'RCA_Category': None,
                        'RCA_Reason': None,
                        'RCA_Retrieval_Date': None,
                        'Lifecycle_Category': None,
                        'Lifecycle_Reason': None,
                        'Lifecycle_Retrieval_Date': None
                    })
            
            # Check if there are more cases
            next_token = response.get('nextToken')
            if not next_token:
                break
        
        logger.info(f"Retrieved {len(cases)} support cases")
        return cases
    except Exception as e:
        # Check if this is an AccessDeniedException or SubscriptionRequiredException
        error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
        if error_code in ['AccessDeniedException', 'SubscriptionRequiredException']:
            logger.warning(f"Support API access issue for account: {error_code}. This is expected for accounts without Business or Enterprise Support.")
            return []  # Return empty list instead of raising exception
        else:
            logger.warning(f"Failed to retrieve support cases: {str(e)}")
            raise

def process_account(account_id: str, bucket_name: str, annotation_queue_url: str) -> int:
    """
    Process an AWS account to retrieve and store support cases.
    
    Args:
        account_id: The AWS account ID.
        bucket_name: The S3 bucket name.
        annotation_queue_url: The SQS queue URL for case annotations.
        
    Returns:
        The number of new cases processed.
    """
    try:
        # Assume the role in the target account
        role_name = os.environ['SUPPORT_ROLE_NAME']
        session_name = f"CaseRetrieval-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"Assuming role {role_name} in account {account_id}")
        session = assume_role(account_id, role_name, session_name)
        
        # Get support cases
        cases = get_support_cases(session)
        
        # If no cases were returned, log and return successfully
        if not cases:
            logger.info(f"No support cases found for account {account_id}")
            return 0
        
        # Create the account folder
        account_folder = f"account_number={account_id}"
        
        # OPTIMIZATION: Check processed bucket as single source of truth
        # Cleanup function handles any failed processing overnight
        processed_bucket_name = os.environ['CASE_PROCESSED_BUCKET']
        existing_cases = get_existing_cases_batch(processed_bucket_name, account_folder)
        logger.info(f"Account {account_id}: {len(cases)} total cases, {len(existing_cases)} existing processed cases")
        
        # Process each case
        new_case_count = 0
        
        for case in cases:
            display_id = case['displayId']
            case_id = case['caseId']
            
            # OPTIMIZATION: Check against batch results instead of individual S3 calls
            if display_id in existing_cases:
                logger.debug(f"Case {display_id} already exists, skipping")
                continue
            
            # Store the case data
            case_folder = f"{account_folder}/case_number={display_id}"
            data_key = f"{case_folder}/data.json"
            write_s3_json(bucket_name, data_key, case)
            
            # Send a message to the annotation queue
            message = {
                'accountId': account_id,
                'displayId': display_id,
                'caseId': case_id
            }
            
            send_sqs_message(annotation_queue_url, message)
            
            new_case_count += 1
            logger.info(f"Processed new case {display_id} for account {account_id}")
        
        logger.info(f"Processed {new_case_count} new cases for account {account_id}")
        return new_case_count
    except Exception as e:
        # Handle role assumption failures gracefully
        if "AccessDenied" in str(e) and "sts:AssumeRole" in str(e):
            logger.warning(f"Access denied when assuming role in account {account_id}. The role may not exist or you may not have permission to assume it.")
            return 0  # Return 0 instead of raising exception
        else:
            logger.warning(f"Failed to process account {account_id}: {str(e)}")
            raise

def lambda_handler(event, context):
    """
    Lambda function handler for CaseRetrieval.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict.
    """
    try:
        # Get parameters from environment variables
        bucket_name = os.environ['CASE_RAW_BUCKET']
        annotation_queue_url = os.environ['CASE_ANNOTATION_QUEUE_URL']
        
        # Process SQS event
        for record in event['Records']:
            if record['eventSource'] == 'aws:sqs':
                # Parse the message
                message = json.loads(record['body'])
                account_id = message.get('accountId')
                
                if not account_id:
                    logger.error("Missing accountId in SQS message")
                    continue
                
                logger.info(f"Processing account {account_id}")
                
                # Process the account
                new_case_count = process_account(account_id, bucket_name, annotation_queue_url)
                
                logger.info(f"Successfully processed {new_case_count} new cases for account {account_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': "Successfully processed accounts"
            })
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise