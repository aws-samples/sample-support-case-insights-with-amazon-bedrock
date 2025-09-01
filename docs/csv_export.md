# CSV Export for Case Insights

This document explains how to export Support Case Insights data to CSV files for analysis with tools like PowerBI, Excel, or other business intelligence platforms. This is particularly useful for customers who don't have access to Amazon Athena.

## Overview

The Support Case Insights solution stores case data in S3 buckets. While Athena provides a convenient way to query this data, you can also export the data to CSV files using the provided script. These CSV files can then be imported into your preferred analytics tool.

## Prerequisites

Before you can export the data to CSV files, you need:

1. Python 3.9 or later installed
2. Required Python packages:
   ```bash
   pip install boto3 pandas
   ```
3. AWS credentials with permissions to access the S3 bucket containing the case data

## Required AWS Permissions

To run the CSV export script, you need AWS credentials with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::s3-<uniqueidentifier>-caseprocessed",
                "arn:aws:s3:::s3-<uniqueidentifier>-caseprocessed/*"
            ]
        }
    ]
}
```

Replace `<uniqueidentifier>` with the unique identifier used when deploying the Support Case Insights solution.

### Creating a Role for CSV Export

If you want to create a dedicated role for CSV export:

1. In the AWS Console, navigate to IAM > Roles > Create role
2. Select "Custom trust policy" and enter:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "arn:aws:iam::<your-account-id>:root"
         },
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```
3. Click Next, then create a new policy with the permissions shown above
4. Name the role (e.g., "CaseInsights-CSVExport-Role") and create it
5. Configure your AWS credentials to use this role when running the script

## Using the CSV Export Script

The script `generate_csv_insights.py` reads case data from the S3 bucket and generates CSV files with insights similar to the Athena queries in the documentation.

### Running the Script

```bash
python3 scripts/generate_csv_insights.py --bucket s3-<uniqueidentifier>-caseprocessed --output ./csv_insights --region <your-region>
```

Replace:
- `<uniqueidentifier>` with the unique identifier used when deploying the Support Case Insights solution
- `<your-region>` with your AWS region (e.g., us-east-1)

### Generated CSV Files

The script generates the following CSV files:

1. **all_cases.csv**: All case data with all fields
2. **cases_by_rca_category.csv**: Count of cases by Root Cause Analysis category
3. **cases_by_lifecycle_category.csv**: Count of cases by Lifecycle category
4. **cases_by_service_rca.csv**: Count of cases by service and RCA category
5. **cases_by_account_rca.csv**: Count of cases by account and RCA category
6. **cases_by_month_rca.csv**: Count of cases by month and RCA category
7. **cases_by_severity_rca.csv**: Count of cases by severity and RCA category
8. **top_services.csv**: Top 10 services with the most cases
9. **trend_by_week.csv**: Trend analysis of cases by week

## Automating CSV Export

You can automate the CSV export process by setting up a scheduled task or cron job to run the script periodically. For example, to run the script daily:

### On Linux/macOS:

Add a cron job:

```bash
0 0 * * * /usr/bin/python3 /path/to/scripts/generate_csv_insights.py --bucket s3-<uniqueidentifier>-caseprocessed --output /path/to/csv_insights --region <your-region>
```

### On Windows:

Create a scheduled task:

1. Open Task Scheduler
2. Create a new task
3. Set the trigger to run daily
4. Set the action to run the script:
   - Program: `python`
   - Arguments: `C:\path\to\scripts\generate_csv_insights.py --bucket s3-<uniqueidentifier>-caseprocessed --output C:\path\to\csv_insights --region <your-region>`

## Troubleshooting

### Common Issues

#### Permission Denied

If you get a permission denied error when accessing the S3 bucket:

1. Verify that your AWS credentials have the required permissions
2. Check that the bucket name is correct
3. Ensure that the bucket policy allows access from your account

#### Missing Dependencies

If you get an error about missing Python dependencies:

```bash
pip install boto3 pandas
```

#### Memory Issues

If you encounter memory issues when processing large datasets:

1. Increase the available memory for Python
2. Process the data in smaller batches by modifying the script

### Getting Help

If you need further assistance:

1. Check the AWS documentation for S3 and IAM
2. Review the script for any customization options
3. Open an issue on the GitHub repository