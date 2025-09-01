import json
import logging
import os
import random
import time
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_parameter(name: str, default: Optional[Any] = None) -> Any:
    """
    Get a parameter from environment variables.
    
    Args:
        name: The name of the parameter.
        default: The default value if the parameter is not found.
        
    Returns:
        The parameter value or the default value.
    """
    return os.environ.get(name, default)

def exponential_backoff(attempt: int, max_attempts: int = 5, base_delay: float = 1.0, jitter: bool = True) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: The current attempt number (0-based).
        max_attempts: The maximum number of attempts.
        base_delay: The base delay in seconds.
        jitter: Whether to add jitter to the delay.
        
    Returns:
        The delay in seconds.
    """
    if attempt >= max_attempts:
        return -1  # Signal that we've exceeded max attempts
    
    # Calculate exponential backoff
    delay = base_delay * (2 ** attempt)
    
    # Add jitter if requested (up to 20% of the delay)
    if jitter:
        delay = delay * (0.8 + 0.2 * random.random())
        
    return delay

def retry_with_backoff(func, *args, max_attempts: int = 5, base_delay: float = 1.0, **kwargs):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: The function to retry.
        *args: Positional arguments to pass to the function.
        max_attempts: The maximum number of attempts.
        base_delay: The base delay in seconds.
        **kwargs: Keyword arguments to pass to the function.
        
    Returns:
        The result of the function call.
        
    Raises:
        Exception: If all retry attempts fail.
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            delay = exponential_backoff(attempt, max_attempts, base_delay)
            
            if delay < 0:  # Max attempts exceeded
                break
                
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    # If we get here, all retries failed
    logger.error(f"All {max_attempts} attempts failed. Last error: {str(last_exception)}")
    raise last_exception

def assume_role(account_id: str, role_name: str, session_name: str) -> boto3.Session:
    """
    Assume a role in another AWS account.
    
    Args:
        account_id: The AWS account ID.
        role_name: The name of the role to assume.
        session_name: The session name.
        
    Returns:
        A boto3 session with the assumed role credentials.
    """
    sts_client = boto3.client('sts')
    
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    
    try:
        response = retry_with_backoff(
            sts_client.assume_role,
            RoleArn=role_arn,
            RoleSessionName=session_name
        )
        
        credentials = response['Credentials']
        
        session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        
        return session
    except Exception as e:
        logger.warning(f"Failed to assume role {role_arn}: {str(e)}")
        raise

def read_s3_json(bucket: str, key: str) -> Dict[str, Any]:
    """
    Read a JSON file from S3.
    
    Args:
        bucket: The S3 bucket name.
        key: The S3 object key.
        
    Returns:
        The parsed JSON data.
    """
    s3_client = boto3.client('s3')
    
    try:
        response = retry_with_backoff(
            s3_client.get_object,
            Bucket=bucket,
            Key=key
        )
        
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Failed to read JSON from S3 {bucket}/{key}: {str(e)}")
        raise

def write_s3_json(bucket: str, key: str, data: Dict[str, Any]) -> None:
    """
    Write JSON data to S3.
    
    Args:
        bucket: The S3 bucket name.
        key: The S3 object key.
        data: The data to write.
    """
    s3_client = boto3.client('s3')
    
    try:
        content = json.dumps(data)
        retry_with_backoff(
            s3_client.put_object,
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType='application/json'
        )
    except Exception as e:
        logger.warning(f"Failed to write JSON to S3 {bucket}/{key}: {str(e)}")
        raise

def check_s3_object_exists(bucket: str, key: str) -> bool:
    """
    Check if an S3 object exists.
    
    Args:
        bucket: The S3 bucket name.
        key: The S3 object key.
        
    Returns:
        True if the object exists, False otherwise.
    """
    s3_client = boto3.client('s3')
    
    try:
        retry_with_backoff(
            s3_client.head_object,
            Bucket=bucket,
            Key=key
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            logger.warning(f"Error checking if S3 object exists {bucket}/{key}: {str(e)}")
            raise

def get_existing_cases_batch(bucket: str, account_folder: str) -> set:
    """
    Get all existing case display IDs for an account using batch S3 operations.
    
    Args:
        bucket: The S3 bucket name.
        account_folder: The account folder prefix (e.g., "account_number=123456789")
        
    Returns:
        A set of existing case display IDs.
    """
    s3_client = boto3.client('s3')
    existing_cases = set()
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        
        # List all objects in the account folder
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{account_folder}/"):
            for obj in page.get('Contents', []):
                # Extract case number from keys like "account_number=123/case_number=456/data.json"
                if obj['Key'].endswith('/data.json'):
                    key_parts = obj['Key'].split('/')
                    if len(key_parts) >= 2:
                        case_part = key_parts[-2]  # Get "case_number=456"
                        if case_part.startswith('case_number='):
                            case_display_id = case_part.split('=')[1]
                            existing_cases.add(case_display_id)
        
        logger.info(f"Found {len(existing_cases)} existing cases in {account_folder}")
        return existing_cases
        
    except Exception as e:
        logger.error(f"Failed to get existing cases for {account_folder}: {str(e)}")
        # Fall back to empty set - will process all cases as new
        return set()

def send_sqs_message(queue_url: str, message_body: Dict[str, Any]) -> str:
    """
    Send a message to an SQS queue.
    
    Args:
        queue_url: The SQS queue URL.
        message_body: The message body.
        
    Returns:
        The message ID.
    """
    sqs_client = boto3.client('sqs')
    
    try:
        response = retry_with_backoff(
            sqs_client.send_message,
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        
        return response['MessageId']
    except Exception as e:
        logger.warning(f"Failed to send message to SQS {queue_url}: {str(e)}")
        raise

def delete_sqs_message(queue_url: str, receipt_handle: str) -> None:
    """
    Delete a message from an SQS queue.
    
    Args:
        queue_url: The SQS queue URL.
        receipt_handle: The receipt handle of the message.
    """
    sqs_client = boto3.client('sqs')
    
    try:
        retry_with_backoff(
            sqs_client.delete_message,
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
    except Exception as e:
        logger.warning(f"Failed to delete message from SQS {queue_url}: {str(e)}")
        raise

def invoke_bedrock(model_id: str, prompt: str, max_tokens: int = 2000) -> str:
    """
    Invoke Amazon Bedrock to generate text.
    
    Args:
        model_id: The model ID.
        prompt: The prompt text.
        max_tokens: The maximum number of tokens to generate.
        
    Returns:
        The generated text.
    """
    bedrock_client = boto3.client('bedrock-runtime')
    
    try:
        # For Claude models
        if "anthropic" in model_id:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        else:
            # Generic fallback for other models
            request_body = {
                "prompt": prompt,
                "max_tokens": max_tokens
            }
        
        response = retry_with_backoff(
            bedrock_client.invoke_model,
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # For Claude models
        if "anthropic" in model_id:
            return response_body['content'][0]['text']
        else:
            # Generic fallback for other models
            return response_body.get('completion', '')
    except Exception as e:
        logger.warning(f"Failed to invoke Bedrock model {model_id}: {str(e)}")
        raise