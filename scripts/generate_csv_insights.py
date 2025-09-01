#!/usr/bin/env python3
"""
AWS Case Insights - CSV Generator

This script reads case data from S3 and generates CSV files with insights
similar to the Athena queries in the documentation. This is useful for
customers who don't have access to Athena but want to analyze the data
using tools like PowerBI.

Usage:
  python3 generate_csv_insights.py --bucket <bucket-name> --output <output-dir> [--region <region>]

Requirements:
  - boto3
  - pandas
"""

import argparse
import boto3
import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate CSV insights from AWS Case Insights data')
    parser.add_argument('--bucket', required=True, help='S3 bucket name containing case data')
    parser.add_argument('--output', required=True, help='Output directory for CSV files')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    return parser.parse_args()


def list_account_folders(s3_client, bucket: str) -> List[str]:
    """List all account folders in the bucket."""
    account_folders = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    # List objects with the account_number= prefix and delimiter /
    for page in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix='account_number='):
        for prefix in page.get('CommonPrefixes', []):
            account_folders.append(prefix.get('Prefix'))
    
    return account_folders


def list_case_folders(s3_client, bucket: str, account_folder: str) -> List[str]:
    """List all case folders in an account folder."""
    case_folders = []
    paginator = s3_client.get_paginator('list_objects_v2')
    
    # List objects with the account_folder prefix and delimiter /
    for page in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=account_folder):
        for prefix in page.get('CommonPrefixes', []):
            case_folders.append(prefix.get('Prefix'))
    
    return case_folders


def get_case_data(s3_client, bucket: str, case_folder: str) -> Dict[str, Any]:
    """Get case data from a case folder."""
    try:
        # Get the data.json file
        response = s3_client.get_object(Bucket=bucket, Key=f"{case_folder}data.json")
        case_data = json.loads(response['Body'].read().decode('utf-8'))
        
        # Extract account_number and case_number from the folder path
        # Format: account_number=123456789012/case_number=12345678910/
        parts = case_folder.strip('/').split('/')
        account_number = parts[0].split('=')[1]
        case_number = parts[1].split('=')[1]
        
        # Add account_number and case_number to the case data
        case_data['account_number'] = account_number
        case_data['case_number'] = case_number
        
        return case_data
    except Exception as e:
        print(f"Error getting case data from {case_folder}: {str(e)}")
        return None


def collect_all_case_data(s3_client, bucket: str) -> List[Dict[str, Any]]:
    """Collect all case data from the bucket."""
    all_case_data = []
    
    # List all account folders
    account_folders = list_account_folders(s3_client, bucket)
    total_accounts = len(account_folders)
    
    print(f"Found {total_accounts} account folders")
    
    # Process each account folder
    for i, account_folder in enumerate(account_folders, 1):
        print(f"Processing account folder {i}/{total_accounts}: {account_folder}")
        
        # List all case folders in the account folder
        case_folders = list_case_folders(s3_client, bucket, account_folder)
        total_cases = len(case_folders)
        
        print(f"  Found {total_cases} case folders")
        
        # Process each case folder
        for j, case_folder in enumerate(case_folders, 1):
            if j % 100 == 0:
                print(f"  Processing case folder {j}/{total_cases}")
            
            # Get case data
            case_data = get_case_data(s3_client, bucket, case_folder)
            if case_data:
                all_case_data.append(case_data)
    
    print(f"Collected data for {len(all_case_data)} cases")
    return all_case_data


def create_dataframe(case_data_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create a pandas DataFrame from the case data."""
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(case_data_list)
    
    # Convert ISO 8601 timestamps to datetime objects
    if 'timeCreated' in df.columns:
        df['timeCreated'] = pd.to_datetime(df['timeCreated'])
    
    return df


def generate_csv_insights(df: pd.DataFrame, output_dir: str):
    """Generate CSV files with insights."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. All case data
    print("Generating all_cases.csv")
    df.to_csv(os.path.join(output_dir, 'all_cases.csv'), index=False)
    
    # 2. Cases by RCA Category
    print("Generating cases_by_rca_category.csv")
    if 'RCA_Category' in df.columns:
        rca_counts = df[df['RCA_Category'].notna()].groupby('RCA_Category').size().reset_index(name='case_count')
        rca_counts = rca_counts.sort_values('case_count', ascending=False)
        rca_counts.to_csv(os.path.join(output_dir, 'cases_by_rca_category.csv'), index=False)
    
    # 3. Cases by Lifecycle Category
    print("Generating cases_by_lifecycle_category.csv")
    if 'Lifecycle_Category' in df.columns:
        lifecycle_counts = df[df['Lifecycle_Category'].notna()].groupby('Lifecycle_Category').size().reset_index(name='case_count')
        lifecycle_counts = lifecycle_counts.sort_values('case_count', ascending=False)
        lifecycle_counts.to_csv(os.path.join(output_dir, 'cases_by_lifecycle_category.csv'), index=False)
    
    # 4. Cases by Service and RCA Category
    print("Generating cases_by_service_rca.csv")
    if all(col in df.columns for col in ['serviceCode', 'RCA_Category']):
        service_rca = df[df['RCA_Category'].notna()].groupby(['serviceCode', 'RCA_Category']).size().reset_index(name='case_count')
        service_rca = service_rca.sort_values(['serviceCode', 'case_count'], ascending=[True, False])
        service_rca.to_csv(os.path.join(output_dir, 'cases_by_service_rca.csv'), index=False)
    
    # 5. Cases by Account and RCA Category
    print("Generating cases_by_account_rca.csv")
    if all(col in df.columns for col in ['account_number', 'RCA_Category']):
        account_rca = df[df['RCA_Category'].notna()].groupby(['account_number', 'RCA_Category']).size().reset_index(name='case_count')
        account_rca = account_rca.sort_values(['account_number', 'case_count'], ascending=[True, False])
        account_rca.to_csv(os.path.join(output_dir, 'cases_by_account_rca.csv'), index=False)
    
    # 6. Cases by Month and RCA Category
    print("Generating cases_by_month_rca.csv")
    if all(col in df.columns for col in ['timeCreated', 'RCA_Category']):
        # Add month column
        df_with_month = df.copy()
        df_with_month['month'] = df_with_month['timeCreated'].dt.strftime('%Y-%m')
        
        month_rca = df_with_month[df_with_month['RCA_Category'].notna()].groupby(['month', 'RCA_Category']).size().reset_index(name='case_count')
        month_rca = month_rca.sort_values(['month', 'case_count'], ascending=[True, False])
        month_rca.to_csv(os.path.join(output_dir, 'cases_by_month_rca.csv'), index=False)
    
    # 7. Cases by Severity and RCA Category
    print("Generating cases_by_severity_rca.csv")
    if all(col in df.columns for col in ['severityCode', 'RCA_Category']):
        severity_rca = df[df['RCA_Category'].notna()].groupby(['severityCode', 'RCA_Category']).size().reset_index(name='case_count')
        severity_rca = severity_rca.sort_values(['severityCode', 'case_count'], ascending=[True, False])
        severity_rca.to_csv(os.path.join(output_dir, 'cases_by_severity_rca.csv'), index=False)
    
    # 8. Top Services with Issues
    print("Generating top_services.csv")
    if 'serviceCode' in df.columns:
        top_services = df.groupby('serviceCode').size().reset_index(name='case_count')
        top_services = top_services.sort_values('case_count', ascending=False).head(10)
        top_services.to_csv(os.path.join(output_dir, 'top_services.csv'), index=False)
    
    # 9. Trend Analysis by Week
    print("Generating trend_by_week.csv")
    if 'timeCreated' in df.columns:
        # Add week column
        df_with_week = df.copy()
        df_with_week['week'] = df_with_week['timeCreated'].dt.strftime('%Y-%U')
        
        week_counts = df_with_week.groupby('week').size().reset_index(name='case_count')
        week_counts = week_counts.sort_values('week')
        week_counts.to_csv(os.path.join(output_dir, 'trend_by_week.csv'), index=False)


def main():
    """Main function."""
    args = parse_args()
    
    # Create S3 client
    s3_client = boto3.client('s3', region_name=args.region)
    
    # Collect all case data
    case_data_list = collect_all_case_data(s3_client, args.bucket)
    
    # Create DataFrame
    df = create_dataframe(case_data_list)
    
    # Generate CSV insights
    generate_csv_insights(df, args.output)
    
    print(f"CSV files generated in {args.output}")


if __name__ == '__main__':
    main()