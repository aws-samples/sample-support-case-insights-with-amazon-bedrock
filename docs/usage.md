# Usage Guide

This guide provides instructions for using the Support Case Insights solution after installation.

## Overview

The Support Case Insights solution automatically collects, processes, and analyzes AWS support cases across multiple accounts within an organization. This guide explains how to use the solution and interpret the results.

## Workflow

The solution follows this workflow:

1. **Account Collection**: Every day, the solution retrieves a list of active accounts from your AWS Organization.
2. **Case Retrieval**: For each account, the solution retrieves resolved support cases from the trailing 12 months. It checks if each case has already been processed and skips existing cases to avoid duplicate processing.
3. **Case Annotation**: For each case, the solution retrieves the communications history.
4. **AI Analysis**: The solution uses Amazon Bedrock to analyze the case and generate insights:
   - Case Summary: A concise summary of the case
   - Root Cause Analysis: Categorization of the root cause
   - Lifecycle Analysis: Identification of lifecycle improvement opportunities
5. **Data Storage**: The raw case data is stored in one S3 bucket during processing, and the complete results with AI insights are stored in a separate processed data S3 bucket for querying and visualization.

## Monitoring the Solution

### CloudWatch Dashboard

The solution creates a CloudWatch dashboard that provides visibility into the system's operation. To access the dashboard:

1. Open the AWS Management Console
2. Navigate to CloudWatch
3. Select "Dashboards" from the left navigation
4. Select the dashboard named "CaseInsights-${UniqueIdentifier}"

The dashboard includes:

- Lambda function metrics (invocations, errors, duration)
- SQS queue metrics (messages received, queue depth)
- Step Function metrics (executions started, succeeded, failed)

### CloudWatch Alarms

The solution creates CloudWatch alarms that notify you of potential issues:

- **LambdaErrorAlarm**: Triggers when Lambda functions have errors
- **StepFunctionFailureAlarm**: Triggers when Step Functions fail
- **DLQMessagesAlarm**: Triggers when messages are sent to dead-letter queues

To configure notifications for these alarms:

1. Open the AWS Management Console
2. Navigate to CloudWatch
3. Select "Alarms" from the left navigation
4. Select the alarm you want to configure
5. Click "Actions" and then "Edit"
6. Add an SNS notification

## Analyzing the Data

You can analyze the data using either Amazon Athena (recommended) or by exporting to CSV files for use with tools like PowerBI.

### Using Athena

The solution stores the data in S3 in a format that can be queried using Amazon Athena. To set up Athena:

NOTE:  In the installation there is an option to enable Analytics which would install all the necessary Athena components but you will still need to run option 3 to rebuild the table as new cases are added.

1. Create an Athena database:

```sql
CREATE DATABASE case_insights;
```

2. Create an external table for the case summary data:

```sql
CREATE EXTERNAL TABLE case_insights.case_summary (
  caseId STRING,
  displayId STRING,
  subject STRING,
  serviceCode STRING,
  categoryCode STRING,
  severityCode STRING,
  submittedBy STRING,
  timeCreated STRING,
  status STRING,
  Case_Retrieval_Date STRING,
  Case_Summary STRING,
  RCA_Category STRING,
  RCA_Reason STRING,
  RCA_Retrieval_Date STRING,
  Lifecycle_Category STRING,
  Lifecycle_Reason STRING,
  Lifecycle_Retrieval_Date STRING
)
PARTITIONED BY (
  account_number STRING,
  case_number STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = '1'
)
LOCATION 's3://s3-<uniqueidentifier>-caseprocessed/'
TBLPROPERTIES ('has_encrypted_data'='false');
```

3. Load the partitions:

```sql
MSCK REPAIR TABLE case_insights.case_summary;
```

### Example Queries

Here are some example queries to get you started:

#### Count Cases by RCA Category

```sql
SELECT
  RCA_Category,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  RCA_Category IS NOT NULL
GROUP BY
  RCA_Category
ORDER BY
  case_count DESC;
```

#### Count Cases by Lifecycle Category

```sql
SELECT
  Lifecycle_Category,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  Lifecycle_Category IS NOT NULL
GROUP BY
  Lifecycle_Category
ORDER BY
  case_count DESC;
```

#### Cases by Service and RCA Category

```sql
SELECT
  serviceCode,
  RCA_Category,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  RCA_Category IS NOT NULL
GROUP BY
  serviceCode,
  RCA_Category
ORDER BY
  serviceCode,
  case_count DESC;
```

For more example queries, see the [Athena Queries](athena.md) document.


### Using CSV Export

If you don't have access to Athena, you can export the data to CSV files for analysis with tools like PowerBI, Excel, or other business intelligence platforms. See the [CSV Export](csv_export.md) document for details.

### Visualizing the Data

You can use Amazon QuickSight to create visualizations and dashboards based on the Athena queries. To set up QuickSight:

1. Open the AWS Management Console
2. Navigate to QuickSight
3. Create a new dataset using Athena as the data source
4. Select the `case_insights` database and the `case_summary` table
5. Create visualizations based on the data

Here are some visualization ideas:

- Pie chart of cases by RCA category
- Bar chart of cases by service
- Line chart of cases over time
- Heat map of cases by account and RCA category

## Troubleshooting

### Common Issues

#### Missing Cases

If you notice that cases are missing from the analysis:

1. Check that the account has the `Support-Case-Analysis-Role` role with the correct permissions
2. Verify that the role's trust policy allows the management account to assume the role
3. Check the CloudWatch Logs for the `Lambda-CaseRetrieval` function for error messages

#### Failed AI Analysis

If the AI analysis is failing:

1. Check the CloudWatch Logs for the Step Functions for error messages
2. Verify that the Bedrock model is available in your region
3. Check that the templates are correctly formatted

#### Athena Query Issues

If you're having issues with Athena queries:

1. Verify that the table schema matches the data structure
2. Run `MSCK REPAIR TABLE` to update the partitions
3. Check that the S3 bucket has the correct permissions

### Getting Help

If you need further assistance:

1. Check the CloudWatch Logs for detailed error messages
2. Review the [Architecture Overview](architecture.md) and [IAM Roles and Permissions](permissions.md) documents
3. Open an issue on the GitHub repository