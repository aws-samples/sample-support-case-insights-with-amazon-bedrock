import json
import logging
import os
from typing import Dict, Tuple

import boto3

from common.utils import invoke_bedrock, read_s3_json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def load_template() -> str:
    """
    Load the summary template.
    
    Returns:
        The template text.
    """
    template_path = os.environ.get('SUMMARY_TEMPLATE_PATH', '/opt/templates/summary-template.txt')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to load template from {template_path}: {str(e)}")
        raise

def generate_case_summary(annotation: Dict, template: str) -> str:
    """
    Generate a case summary using Bedrock.
    
    Args:
        annotation: The case annotation.
        template: The template text.
        
    Returns:
        The generated summary.
    """
    # Extract the case annotation text
    communications = annotation.get('communications', [])
    annotation_text = "\n\n".join([
        f"Time: {comm.get('timeCreated', '')}\nFrom: {comm.get('submittedBy', '')}\nMessage: {comm.get('body', '')}"
        for comm in communications
    ])
    
    # Replace the placeholder in the template
    prompt = template.replace('{case_annotation}', annotation_text)
    
    # Invoke Bedrock
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-haiku-20241022-v1:0')
    max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '2000'))
    
    logger.info(f"Invoking Bedrock model {model_id} with max tokens {max_tokens}")
    
    summary = invoke_bedrock(model_id, prompt, max_tokens)
    
    logger.info(f"Generated summary of length {len(summary)}")
    return summary

def lambda_handler(event, context):
    """
    Lambda function handler for Step-CaseSummary.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict with the case summary.
    """
    try:
        # Get the file path from the event
        file_path = event.get('filePath')
        receipt_handle = event.get('receiptHandle')
        
        if not file_path:
            raise ValueError("Missing filePath in event")
        
        logger.info(f"Processing file path: {file_path}")
        
        # Parse the file path to get the bucket and key
        parts = file_path.split('/', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid file path format: {file_path}")
        
        bucket_name = parts[0]
        folder_path = parts[1]
        annotation_key = f"{folder_path}/annotation.json"
        
        # Read the annotation from S3
        annotation = read_s3_json(bucket_name, annotation_key)
        
        # Load the template
        template = load_template()
        
        # Generate the case summary
        case_summary = generate_case_summary(annotation, template)
        
        # Return the result
        return {
            'filePath': file_path,
            'receiptHandle': receipt_handle,
            'caseSummary': case_summary
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise