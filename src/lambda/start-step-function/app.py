import json
import logging
import os
from typing import Dict

import boto3

from common.utils import retry_with_backoff

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def start_step_function(state_machine_arn: str, input_data: Dict) -> str:
    """
    Start a Step Function execution.
    
    Args:
        state_machine_arn: The ARN of the state machine.
        input_data: The input data for the execution.
        
    Returns:
        The execution ARN.
    """
    sfn_client = boto3.client('stepfunctions')
    
    try:
        response = retry_with_backoff(
            sfn_client.start_execution,
            stateMachineArn=state_machine_arn,
            input=json.dumps(input_data)
        )
        
        execution_arn = response['executionArn']
        logger.info(f"Started Step Function execution: {execution_arn}")
        return execution_arn
    except Exception as e:
        logger.warning(f"Failed to start Step Function execution: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda function handler for StartStepFunction.
    
    Args:
        event: The event dict.
        context: The context object.
        
    Returns:
        The response dict.
    """
    try:
        # Get parameters from environment variables
        state_machine_arn = os.environ['CASE_ANALYSIS_STATE_MACHINE_ARN']
        
        executions = []
        
        # Process SQS event
        for record in event['Records']:
            if record['eventSource'] == 'aws:sqs':
                # Parse the message
                message = json.loads(record['body'])
                file_path = message.get('filePath')
                receipt_handle = record.get('receiptHandle')
                
                if not file_path:
                    logger.error("Missing filePath in SQS message")
                    continue
                
                logger.info(f"Processing file path: {file_path}")
                
                # Start the Step Function
                input_data = {
                    'filePath': file_path,
                    'receiptHandle': receipt_handle
                }
                
                execution_arn = start_step_function(state_machine_arn, input_data)
                executions.append(execution_arn)
        
        logger.info(f"Started {len(executions)} Step Function executions")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Started {len(executions)} Step Function executions",
                'executions': executions
            })
        }
    except Exception as e:
        # nosec - Final error handling in lambda_handler, error level appropriate
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise