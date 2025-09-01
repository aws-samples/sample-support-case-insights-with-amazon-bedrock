import json
import logging
import os
from datetime import datetime
from typing import Dict

import boto3

from common.utils import delete_sqs_message, read_s3_json, write_s3_json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def update_case_metadata(
    raw_bucket_name: str,
    processed_bucket_name: str,
    folder_path: str,
    case_summary: str,
    rca_category: str,
    rca_reason: str,
    lifecycle_category: str,
    lifecycle_reason: str
) -> None:
    """
    Update the case metadata with AI insights.
    
    Args:
        raw_bucket_name: The S3 bucket name for raw data.
        processed_bucket_name: The S3 bucket name for processed data.
        folder_path: The folder path.
        case_summary: The case summary.
        rca_category: The RCA category.
        rca_reason: The RCA reason.
        lifecycle_category: The lifecycle category.
        lifecycle_reason: The lifecycle reason.
    """
    # Read the existing data.json from raw bucket
    data_key = f"{folder_path}/data.json"
    data = read_s3_json(raw_bucket_name, data_key)
    
    # Update the data with AI insights
    current_time = datetime.utcnow().isoformat()
    
    data.update({
        'Case_Summary': case_summary,
        'RCA_Category': rca_category,
        'RCA_Reason': rca_reason,
        'RCA_Retrieval_Date': current_time,
        'Lifecycle_Category': lifecycle_category,
        'Lifecycle_Reason': lifecycle_reason,
        'Lifecycle_Retrieval_Date': current_time
    })
    
    # Write the complete data to processed bucket as data.json
    processed_data_key = f"{folder_path}/data.json"
    write_s3_json(processed_bucket_name, processed_data_key, data)
    
    logger.info(f"Updated metadata for {raw_bucket_name}/{folder_path} -> {processed_bucket_name}/{folder_path}")

def lambda_handler(event, context):
    """
    Lambda function handler for Step-UpdateCaseMetadata.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict.
    """
    try:
        # Get the data from the event
        file_path = event.get('filePath')
        receipt_handle = event.get('receiptHandle')
        case_summary = event.get('caseSummary')
        rca_category = event.get('rcaCategory')
        rca_reason = event.get('rcaReason')
        lifecycle_category = event.get('lifecycleCategory')
        lifecycle_reason = event.get('lifecycleReason')
        
        if not all([file_path, case_summary, rca_category, rca_reason, lifecycle_category, lifecycle_reason]):
            raise ValueError("Missing required fields in event")
        
        logger.info(f"Updating metadata for {file_path}")
        
        # Parse the file path to get the bucket and folder
        parts = file_path.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid file path format: {file_path}")
        
        raw_bucket_name = parts[0]
        folder_path = parts[1]
        
        # Get processed bucket from environment
        processed_bucket_name = os.environ.get('CASE_PROCESSED_BUCKET')
        if not processed_bucket_name:
            raise ValueError("CASE_PROCESSED_BUCKET environment variable not set")
        
        # Update the case metadata
        update_case_metadata(
            raw_bucket_name,
            processed_bucket_name,
            folder_path,
            case_summary,
            rca_category,
            rca_reason,
            lifecycle_category,
            lifecycle_reason
        )
        
        # Delete the SQS message if receipt handle is provided
        if receipt_handle:
            queue_url = os.environ.get('CASE_SUMMARY_QUEUE_URL')
            if queue_url:
                delete_sqs_message(queue_url, receipt_handle)
                logger.info(f"Deleted message with receipt handle {receipt_handle}")
        
        # Return success
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Successfully updated metadata for {file_path}"
            })
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise