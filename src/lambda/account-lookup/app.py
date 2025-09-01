import json
import logging
import os
from datetime import datetime
from typing import Dict, List

import boto3

from common.utils import retry_with_backoff, write_s3_json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_active_accounts(organization_id: str) -> List[Dict[str, str]]:
    """
    Get a list of active accounts in the specified organization.
    
    Args:
        organization_id: The AWS Organization ID.
        
    Returns:
        A list of active accounts with their IDs and names.
    """
    organizations_client = boto3.client('organizations')
    accounts = []
    
    try:
        paginator = organizations_client.get_paginator('list_accounts')
        
        for page in paginator.paginate():
            for account in page['Accounts']:
                # Only include active accounts
                if account['Status'] == 'ACTIVE':
                    accounts.append({
                        'accountId': account['Id'],
                        'accountName': account['Name']
                    })
        
        logger.info(f"Found {len(accounts)} active accounts in organization {organization_id}")
        return accounts
    except Exception as e:
        logger.warning(f"Failed to list accounts in organization {organization_id}: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda function handler for AccountLookup.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict.
    """
    try:
        # Get parameters from environment variables
        organization_id = os.environ['ORGANIZATION_ID']
        bucket_name = os.environ['ACCOUNT_LIST_BUCKET']
        file_key = 'active_aws_accounts.json'
        
        logger.info(f"Starting account lookup for organization {organization_id}")
        
        # Get active accounts
        accounts = get_active_accounts(organization_id)
        
        # Create the JSON data
        data = {
            'accounts': accounts,
            'timestamp': datetime.utcnow().isoformat(),
            'count': len(accounts)
        }
        
        # Write to S3
        write_s3_json(bucket_name, file_key, data)
        
        logger.info(f"Successfully wrote {len(accounts)} accounts to S3 bucket {bucket_name}/{file_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Successfully processed {len(accounts)} accounts",
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise