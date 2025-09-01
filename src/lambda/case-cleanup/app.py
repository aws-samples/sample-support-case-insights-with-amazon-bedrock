import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def list_account_folders(s3_client, bucket: str) -> List[str]:
    """
    List all account folders in the bucket.
    
    Args:
        s3_client: The S3 client.
        bucket: The S3 bucket name.
        
    Returns:
        A list of account folder prefixes.
    """
    account_folders = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        
        # List objects with the account_number= prefix and delimiter /
        for page in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix='account_number='):
            for prefix in page.get('CommonPrefixes', []):
                account_folders.append(prefix.get('Prefix'))
        
        logger.info(f"Found {len(account_folders)} account folders")
        return account_folders
    except Exception as e:
        logger.warning(f"Failed to list account folders: {str(e)}")
        raise

def list_case_folders(s3_client, bucket: str, account_folder: str) -> List[str]:
    """
    List all case folders in an account folder.
    
    Args:
        s3_client: The S3 client.
        bucket: The S3 bucket name.
        account_folder: The account folder prefix.
        
    Returns:
        A list of case folder prefixes.
    """
    case_folders = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        
        # List objects with the account_folder prefix and delimiter /
        for page in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=account_folder):
            for prefix in page.get('CommonPrefixes', []):
                case_folders.append(prefix.get('Prefix'))
        
        return case_folders
    except Exception as e:
        logger.warning(f"Failed to list case folders for {account_folder}: {str(e)}")
        raise

def check_case_completion(s3_client, processed_bucket: str, case_folder: str) -> bool:
    """
    Check if a case has completed processing by looking for data.json in processed bucket.
    
    Args:
        s3_client: The S3 client.
        processed_bucket: The processed S3 bucket name.
        case_folder: The case folder prefix.
        
    Returns:
        True if the case is complete (has data.json in processed bucket), False otherwise.
    """
    processed_key = f"{case_folder}data.json"
    
    try:
        s3_client.head_object(Bucket=processed_bucket, Key=processed_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            logger.warning(f"Error checking completion for {case_folder}: {str(e)}")
            raise

def get_case_info_from_folder(case_folder: str) -> Tuple[str, str]:
    """
    Extract account ID and case ID from case folder path.
    
    Args:
        case_folder: The case folder path (e.g., "account_number=123/case_number=456/")
        
    Returns:
        A tuple of (account_id, case_id).
    """
    try:
        # Format: account_number=123456789012/case_number=12345678910/
        parts = case_folder.strip('/').split('/')
        account_id = parts[0].split('=')[1]
        case_id = parts[1].split('=')[1]
        return account_id, case_id
    except (IndexError, ValueError) as e:
        logger.warning(f"Failed to parse case folder path {case_folder}: {str(e)}")
        raise

def should_skip_account(account_id: str, excluded_accounts: List[str]) -> bool:
    """
    Check if an account should be skipped during cleanup.
    
    Args:
        account_id: The AWS account ID.
        excluded_accounts: List of account IDs to exclude.
        
    Returns:
        True if the account should be skipped, False otherwise.
    """
    return account_id in excluded_accounts

def list_objects_in_case_folder(s3_client, bucket: str, case_folder: str) -> List[str]:
    """
    List all objects in a case folder.
    
    Args:
        s3_client: The S3 client.
        bucket: The S3 bucket name.
        case_folder: The case folder prefix.
        
    Returns:
        A list of object keys in the folder.
    """
    objects = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket, Prefix=case_folder):
            for obj in page.get('Contents', []):
                objects.append(obj['Key'])
        
        return objects
    except Exception as e:
        logger.warning(f"Failed to list objects in {case_folder}: {str(e)}")
        raise

def delete_objects_from_bucket(s3_client, bucket: str, objects: List[str]) -> bool:
    """
    Delete objects from a specific bucket.
    
    Args:
        s3_client: The S3 client.
        bucket: The S3 bucket name.
        objects: List of object keys to delete.
        
    Returns:
        True if deletion was successful, False otherwise.
    """
    try:
        batch_size = 1000  # S3 delete_objects limit
        
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            delete_objects = [{'Key': obj_key} for obj_key in batch]
            
            response = s3_client.delete_objects(
                Bucket=bucket,
                Delete={'Objects': delete_objects}
            )
            
            if 'Errors' in response and response['Errors']:
                for error in response['Errors']:
                    # nosec B608 - This is logging, not SQL. Data comes from trusted AWS API response
                    logger.error(f"Failed to delete {error['Key']} from {bucket}: {error['Code']} - {error['Message']}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete objects from bucket {bucket}: {str(e)}")
        return False

def delete_case_folder(s3_client, raw_bucket: str, processed_bucket: str, case_folder: str, dry_run: bool = False) -> bool:
    """
    Delete all objects in a case folder from both raw and processed buckets.
    
    Args:
        s3_client: The S3 client.
        raw_bucket: The raw S3 bucket name.
        processed_bucket: The processed S3 bucket name.
        case_folder: The case folder prefix.
        dry_run: If True, log actions without deleting.
        
    Returns:
        True if deletion was successful (or would be in dry-run), False otherwise.
    """
    try:
        # List objects in both buckets
        raw_objects = list_objects_in_case_folder(s3_client, raw_bucket, case_folder)
        processed_objects = list_objects_in_case_folder(s3_client, processed_bucket, case_folder)
        
        total_objects = len(raw_objects) + len(processed_objects)
        
        if total_objects == 0:
            logger.warning(f"No objects found in case folder {case_folder} in either bucket")
            return True
        
        account_id, case_id = get_case_info_from_folder(case_folder)
        
        if dry_run:
            logger.info(f"DRY RUN: Would delete {len(raw_objects)} raw objects and {len(processed_objects)} processed objects for case {case_id} in account {account_id}")
            return True
        
        # Delete from raw bucket
        deleted_count = 0
        if raw_objects:
            success = delete_objects_from_bucket(s3_client, raw_bucket, raw_objects)
            if success:
                deleted_count += len(raw_objects)
            else:
                return False
        
        # Delete from processed bucket
        if processed_objects:
            success = delete_objects_from_bucket(s3_client, processed_bucket, processed_objects)
            if success:
                deleted_count += len(processed_objects)
            else:
                return False
        
        logger.info(f"Successfully deleted {deleted_count} objects for case {case_id} in account {account_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete case folder {case_folder}: {str(e)}")
        return False

def identify_incomplete_cases(s3_client, raw_bucket: str, processed_bucket: str, excluded_accounts: List[str]) -> List[str]:
    """
    Identify all incomplete cases by checking raw bucket for data and processed bucket for completion.
    
    Args:
        s3_client: The S3 client.
        raw_bucket: The raw S3 bucket name.
        processed_bucket: The processed S3 bucket name.
        excluded_accounts: List of account IDs to exclude.
        
    Returns:
        A list of incomplete case folder paths.
    """
    incomplete_cases = []
    
    try:
        # Get all account folders from raw bucket (where case discovery happens)
        account_folders = list_account_folders(s3_client, raw_bucket)
        
        for account_folder in account_folders:
            try:
                # Extract account ID and check if it should be skipped
                account_id = account_folder.split('=')[1].rstrip('/')
                
                if should_skip_account(account_id, excluded_accounts):
                    logger.info(f"Skipping excluded account {account_id}")
                    continue
                
                # Get all case folders for this account from raw bucket
                case_folders = list_case_folders(s3_client, raw_bucket, account_folder)
                
                logger.info(f"Checking {len(case_folders)} cases in account {account_id}")
                
                for case_folder in case_folders:
                    # Check if the case is complete (has data.json in processed bucket)
                    if not check_case_completion(s3_client, processed_bucket, case_folder):
                        incomplete_cases.append(case_folder)
                        account_id, case_id = get_case_info_from_folder(case_folder)
                        logger.info(f"Found incomplete case {case_id} in account {account_id}")
                
            except Exception as e:
                logger.error(f"Error processing account folder {account_folder}: {str(e)}")
                continue
        
        logger.info(f"Found {len(incomplete_cases)} incomplete cases total")
        return incomplete_cases
        
    except Exception as e:
        logger.warning(f"Failed to identify incomplete cases: {str(e)}")
        raise

def get_configuration() -> Dict[str, any]:
    """
    Get configuration from environment variables.
    
    Returns:
        A dictionary containing configuration values.
    """
    config = {
        'raw_bucket_name': os.environ.get('CASE_RAW_BUCKET'),
        'processed_bucket_name': os.environ.get('CASE_PROCESSED_BUCKET'),
        'dry_run': os.environ.get('DRY_RUN', 'false').lower() == 'true',
        'max_deletions': int(os.environ.get('MAX_DELETIONS_PER_RUN', '1000')),
        'excluded_accounts': [
            account.strip() 
            for account in os.environ.get('EXCLUDED_ACCOUNTS', '').split(',') 
            if account.strip()
        ]
    }
    
    # Validate required configuration
    if not config['raw_bucket_name']:
        raise ValueError("CASE_RAW_BUCKET environment variable is required")
    if not config['processed_bucket_name']:
        raise ValueError("CASE_PROCESSED_BUCKET environment variable is required")
    
    logger.info(f"Configuration: raw_bucket={config['raw_bucket_name']}, processed_bucket={config['processed_bucket_name']}, dry_run={config['dry_run']}, "
                f"max_deletions={config['max_deletions']}, excluded_accounts={len(config['excluded_accounts'])}")
    
    return config

def validate_cleanup_safety(incomplete_cases: List[str], max_deletions: int) -> List[str]:
    """
    Apply safety checks and limits to the cleanup operation.
    
    Args:
        incomplete_cases: List of incomplete case folders.
        max_deletions: Maximum number of cases to delete in one run.
        
    Returns:
        A filtered list of cases to delete.
    """
    if len(incomplete_cases) == 0:
        logger.info("No incomplete cases found - nothing to clean up")
        return []
    
    if len(incomplete_cases) > max_deletions:
        logger.warning(f"Found {len(incomplete_cases)} incomplete cases, but limiting to {max_deletions} per run")
        # Sort to ensure consistent ordering across runs
        incomplete_cases.sort()
        return incomplete_cases[:max_deletions]
    
    logger.info(f"Will process {len(incomplete_cases)} incomplete cases")
    return incomplete_cases

def perform_cleanup_batch(s3_client, raw_bucket: str, processed_bucket: str, case_folders: List[str], dry_run: bool) -> Tuple[int, int]:
    """
    Perform cleanup on a batch of case folders from both buckets.
    
    Args:
        s3_client: The S3 client.
        raw_bucket: The raw S3 bucket name.
        processed_bucket: The processed S3 bucket name.
        case_folders: List of case folders to clean up.
        dry_run: If True, log actions without deleting.
        
    Returns:
        A tuple of (successful_deletions, failed_deletions).
    """
    successful = 0
    failed = 0
    
    for case_folder in case_folders:
        try:
            if delete_case_folder(s3_client, raw_bucket, processed_bucket, case_folder, dry_run):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Unexpected error deleting {case_folder}: {str(e)}")
            failed += 1
    
    return successful, failed

def publish_cloudwatch_metrics(accounts_processed: int, cases_scanned: int, cases_removed: int, errors: int):
    """
    Publish custom metrics to CloudWatch.
    
    Args:
        accounts_processed: Number of accounts processed.
        cases_scanned: Number of cases scanned.
        cases_removed: Number of cases removed.
        errors: Number of errors encountered.
    """
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        metrics = [
            {
                'MetricName': 'AccountsProcessed',
                'Value': accounts_processed,
                'Unit': 'Count'
            },
            {
                'MetricName': 'CasesScanned',
                'Value': cases_scanned,
                'Unit': 'Count'
            },
            {
                'MetricName': 'CasesRemoved',
                'Value': cases_removed,
                'Unit': 'Count'
            },
            {
                'MetricName': 'Errors',
                'Value': errors,
                'Unit': 'Count'
            }
        ]
        
        # Add timestamp to all metrics
        timestamp = datetime.utcnow()
        for metric in metrics:
            metric['Timestamp'] = timestamp
        
        cloudwatch.put_metric_data(
            Namespace='CaseInsights/Cleanup',
            MetricData=metrics
        )
        
        logger.info(f"Published CloudWatch metrics: accounts={accounts_processed}, "
                   f"scanned={cases_scanned}, removed={cases_removed}, errors={errors}")
        
    except Exception as e:
        logger.error(f"Failed to publish CloudWatch metrics: {str(e)}")
        # Don't raise - metrics failure shouldn't fail the cleanup

def log_cleanup_summary(start_time: datetime, accounts_processed: int, cases_scanned: int, 
                       cases_removed: int, errors: int, dry_run: bool):
    """
    Log a comprehensive summary of the cleanup operation.
    
    Args:
        start_time: When the cleanup started.
        accounts_processed: Number of accounts processed.
        cases_scanned: Number of cases scanned.
        cases_removed: Number of cases removed.
        errors: Number of errors encountered.
        dry_run: Whether this was a dry run.
    """
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    mode = "DRY RUN" if dry_run else "LIVE"
    
    logger.info(f"=== CLEANUP SUMMARY ({mode}) ===")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Accounts processed: {accounts_processed}")
    logger.info(f"Cases scanned: {cases_scanned}")
    logger.info(f"Cases removed: {cases_removed}")
    logger.info(f"Errors encountered: {errors}")
    
    if dry_run:
        logger.info("This was a dry run - no actual deletions were performed")
    elif cases_removed > 0:
        logger.info(f"Successfully cleaned up {cases_removed} incomplete cases")
    else:
        logger.info("No incomplete cases found - data quality is good!")
    
    if errors > 0:
        logger.warning(f"Encountered {errors} errors during cleanup - check logs for details")

def log_error_with_context(operation: str, context: str, error: Exception):
    """
    Log an error with additional context information.
    
    Args:
        operation: The operation that failed.
        context: Additional context (e.g., account ID, case ID).
        error: The exception that occurred.
    """
    logger.error(f"Error during {operation} for {context}: {str(error)}")
    logger.error(f"Error type: {type(error).__name__}")
    
    # Log additional details for specific error types
    if hasattr(error, 'response'):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"AWS Error Code: {error_code}")

def count_total_cases(s3_client, bucket: str, account_folders: List[str], excluded_accounts: List[str]) -> int:
    """
    Count the total number of cases across all accounts for metrics.
    
    Args:
        s3_client: The S3 client.
        bucket: The S3 bucket name.
        account_folders: List of account folder prefixes.
        excluded_accounts: List of account IDs to exclude.
        
    Returns:
        Total number of cases found.
    """
    total_cases = 0
    
    for account_folder in account_folders:
        try:
            account_id = account_folder.split('=')[1].rstrip('/')
            
            if should_skip_account(account_id, excluded_accounts):
                continue
            
            case_folders = list_case_folders(s3_client, bucket, account_folder)
            total_cases += len(case_folders)
            
        except Exception as e:
            logger.error(f"Error counting cases in {account_folder}: {str(e)}")
            continue
    
    return total_cases

def cleanup_incomplete_cases(config: Dict[str, any]) -> Dict[str, any]:
    """
    Main cleanup function that orchestrates the entire process.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        A dictionary with cleanup results.
    """
    start_time = datetime.utcnow()
    s3_client = boto3.client('s3')
    
    # Initialize counters
    accounts_processed = 0
    cases_scanned = 0
    cases_removed = 0
    errors = 0
    
    try:
        logger.info(f"Starting case cleanup for raw bucket {config['raw_bucket_name']} and processed bucket {config['processed_bucket_name']}")
        
        # Get all account folders from raw bucket (where case discovery happens)
        account_folders = list_account_folders(s3_client, config['raw_bucket_name'])
        
        if not account_folders:
            logger.info("No account folders found - nothing to process")
            return {
                'accounts_processed': 0,
                'cases_scanned': 0,
                'cases_removed': 0,
                'errors': 0,
                'duration_seconds': 0
            }
        
        # Count total cases for metrics from raw bucket
        cases_scanned = count_total_cases(s3_client, config['raw_bucket_name'], account_folders, config['excluded_accounts'])
        accounts_processed = len([af for af in account_folders if not should_skip_account(af.split('=')[1].rstrip('/'), config['excluded_accounts'])])
        
        logger.info(f"Will process {accounts_processed} accounts with {cases_scanned} total cases")
        
        # Identify incomplete cases
        incomplete_cases = identify_incomplete_cases(s3_client, config['raw_bucket_name'], config['processed_bucket_name'], config['excluded_accounts'])
        
        # Apply safety checks and limits
        cases_to_cleanup = validate_cleanup_safety(incomplete_cases, config['max_deletions'])
        
        if cases_to_cleanup:
            # Perform the cleanup
            successful, failed = perform_cleanup_batch(
                s3_client, 
                config['raw_bucket_name'],
                config['processed_bucket_name'], 
                cases_to_cleanup, 
                config['dry_run']
            )
            
            cases_removed = successful
            errors = failed
            
            if not config['dry_run']:
                logger.info(f"Cleanup completed: {successful} successful, {failed} failed")
            else:
                logger.info(f"Dry run completed: would have removed {successful} cases")
        
    except Exception as e:
        logger.error(f"Fatal error during cleanup: {str(e)}")
        errors += 1
        raise
    
    finally:
        # Log summary and publish metrics
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        log_cleanup_summary(start_time, accounts_processed, cases_scanned, cases_removed, errors, config['dry_run'])
        
        # Only publish metrics if not in dry run mode
        if not config['dry_run']:
            publish_cloudwatch_metrics(accounts_processed, cases_scanned, cases_removed, errors)
    
    return {
        'accounts_processed': accounts_processed,
        'cases_scanned': cases_scanned,
        'cases_removed': cases_removed,
        'errors': errors,
        'duration_seconds': duration,
        'dry_run': config['dry_run']
    }

def lambda_handler(event, context):
    """
    Lambda function handler for case cleanup.
    
    Args:
        event: The event dict (from CloudWatch Events).
        context: The context object.
        
    Returns:
        The response dict with cleanup results.
    """
    try:
        logger.info("Case cleanup Lambda started")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Get configuration
        config = get_configuration()
        
        # Perform the cleanup
        results = cleanup_incomplete_cases(config)
        
        # Prepare response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Case cleanup completed successfully',
                'results': results
            })
        }
        
        logger.info(f"Case cleanup completed successfully: {results}")
        return response
        
    except Exception as e:
        logger.error(f"Case cleanup failed: {str(e)}")
        
        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Case cleanup failed',
                'error': str(e)
            })
        }