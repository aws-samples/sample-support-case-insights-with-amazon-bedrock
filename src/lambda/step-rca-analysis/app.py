import json
import logging
import os
from typing import Dict, Tuple

import boto3

from common.utils import invoke_bedrock

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def extract_json_from_response(response: str) -> str:
    """
    Extract JSON from the AI response, handling cases where there might be extra text or multiple JSON objects.
    
    Args:
        response: The raw response from the AI model.
        
    Returns:
        The extracted JSON string (first valid JSON object if multiple are present).
    """
    import re
    
    # Remove markdown code blocks if present
    if '```json' in response:
        start = response.find('```json') + 7
        end = response.find('```', start)
        if end != -1:
            response = response[start:end].strip()
    elif '```' in response:
        start = response.find('```') + 3
        end = response.find('```', start)
        if end != -1:
            response = response[start:end].strip()
    
    # Find the first complete JSON object by counting braces
    start = response.find('{')
    if start == -1:
        return response.strip()
    
    brace_count = 0
    end = start
    
    for i in range(start, len(response)):
        if response[i] == '{':
            brace_count += 1
        elif response[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    
    if brace_count == 0:
        # Found a complete JSON object
        json_str = response[start:end+1]
        
        # Try to fix common JSON formatting issues
        json_str = fix_json_formatting(json_str)
        
        logger.info(f"Extracted first JSON object from response (length: {len(json_str)})")
        return json_str
    
    # Fallback: use the original method if brace counting fails
    end = response.rfind('}')
    if start != -1 and end != -1 and end > start:
        json_str = response[start:end+1]
        json_str = fix_json_formatting(json_str)
        return json_str
    
    # If no braces found, return the original response
    return response.strip()

def fix_json_formatting(json_str: str) -> str:
    """
    Fix common JSON formatting issues from AI responses.
    
    Args:
        json_str: The JSON string to fix.
        
    Returns:
        The fixed JSON string.
    """
    import re
    
    # Clean up the response - remove invisible characters and normalize whitespace
    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Remove control characters
    json_str = re.sub(r'\s+', ' ', json_str)  # Normalize whitespace
    json_str = json_str.strip()
    
    # Fix missing comma between "RCA_Category" and "RCA_Reason"
    # Pattern: "RCA_Category": "value""RCA_Reason"
    json_str = re.sub(r'("RCA_Category"\s*:\s*"[^"]*")("RCA_Reason")', r'\1,\2', json_str)
    
    # Fix missing comma between any two quoted key-value pairs
    # Pattern: "key": "value""key2"
    json_str = re.sub(r'(":\s*"[^"]*")("[\w_]+"\s*:)', r'\1,\2', json_str)
    
    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    return json_str

def load_template() -> str:
    """
    Load the RCA template.
    
    Returns:
        The template text.
    """
    template_path = os.environ.get('RCA_TEMPLATE_PATH', '/opt/templates/rca-template.txt')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to load template from {template_path}: {str(e)}")
        raise

def analyze_root_cause(case_summary: str, template: str) -> Tuple[str, str]:
    """
    Analyze the root cause using Bedrock.
    
    Args:
        case_summary: The case summary.
        template: The template text.
        
    Returns:
        A tuple of (RCA_Category, RCA_Reason).
    """
    # Replace the placeholder in the template
    prompt = template.replace('{Case_Summary}', case_summary)
    
    # Invoke Bedrock
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-haiku-20241022-v1:0')
    max_tokens = int(os.environ.get('BEDROCK_MAX_TOKENS', '2000'))
    
    logger.info(f"Invoking Bedrock model {model_id} with max tokens {max_tokens}")
    
    response = invoke_bedrock(model_id, prompt, max_tokens)
    
    logger.info(f"Generated RCA analysis of length {len(response)}")
    
    # Parse the JSON response
    try:
        # Try to extract JSON from the response
        json_str = extract_json_from_response(response)
        rca_data = json.loads(json_str)
        rca_category = rca_data.get('RCA_Category', '')
        rca_reason = rca_data.get('RCA_Reason', '')
        
        return rca_category, rca_reason
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse RCA response as JSON: {str(e)}")
        logger.warning(f"Response: {response}")
        raise

def lambda_handler(event, context):
    """
    Lambda function handler for Step-RCAAnalysis.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict with the RCA analysis.
    """
    try:
        # Get the case summary from the event
        file_path = event.get('filePath')
        receipt_handle = event.get('receiptHandle')
        case_summary = event.get('caseSummary')
        
        if not all([file_path, case_summary]):
            raise ValueError("Missing required fields in event")
        
        logger.info(f"Processing case summary for {file_path}")
        
        # Load the template
        template = load_template()
        
        # Analyze the root cause
        rca_category, rca_reason = analyze_root_cause(case_summary, template)
        
        # Return the result
        return {
            'filePath': file_path,
            'receiptHandle': receipt_handle,
            'caseSummary': case_summary,
            'rcaCategory': rca_category,
            'rcaReason': rca_reason
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise