# Athena Queries for Case Insights

This document provides example Athena queries for analyzing the case insights data.

## Analytics Setup Options

The Support Case Insights solution supports two approaches for setting up analytics components:

### Automated Analytics Setup (Recommended)

When deploying the CloudFormation template, you can set the `EnableAnalytics` parameter to `true` to automatically create:
- Athena database and external table
- Glue catalog resources
- Athena workgroup with proper configuration

This approach eliminates manual setup steps and ensures consistent configuration across deployments.

**Benefits:**
- No manual database or table creation required
- Automated IAM role configuration
- Consistent setup across environments
- Easier maintenance and updates

**To use automated setup:**
1. Deploy the CloudFormation stack with `EnableAnalytics=true`
2. Configure IAM permissions for Athena queries (see below)
3. Skip the "Prerequisites" section below  
4. Proceed directly to running queries or setting up QuickSight

The automated setup creates all necessary resources including the Athena query results bucket.

### Required IAM Permissions

**Important**: Athena ExecutionRoles are not currently supported in all AWS regions, so queries will use your user credentials. You need the following IAM permissions to execute Athena queries:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "athena:BatchGetQueryExecution",
                "athena:GetQueryExecution", 
                "athena:GetQueryResults",
                "athena:StartQueryExecution",
                "athena:StopQueryExecution",
                "athena:GetWorkGroup"
            ],
            "Resource": [
                "arn:aws:athena:*:*:workgroup/CaseInsights-<your-unique-identifier>",
                "arn:aws:athena:*:*:workgroup/primary"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "glue:GetDatabase",
                "glue:GetTable",
                "glue:GetPartitions"
            ],
            "Resource": [
                "arn:aws:glue:<region>:<account-id>:catalog",
                "arn:aws:glue:<region>:<account-id>:database/case_insights_<your-unique-identifier>",
                "arn:aws:glue:<region>:<account-id>:table/case_insights_<your-unique-identifier>/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::s3-<your-unique-identifier>-caseprocessed",
                "arn:aws:s3:::s3-<your-unique-identifier>-caseprocessed/*",
                "arn:aws:s3:::s3-<your-unique-identifier>-athena-results",
                "arn:aws:s3:::s3-<your-unique-identifier>-athena-results/*"
            ]
        }
    ]
}
```

Replace `<your-unique-identifier>` with your actual UniqueIdentifier value. For detailed setup instructions, see the [Installation Guide](installation.md#athena-query-permissions).


## Alternative: CSV Export Script

Regardless of whether you use automated or manual analytics setup, the CSV export script remains available in the `scripts/generate_csv_insights.py` file. This script provides an alternative way to export case insights data without requiring Athena or QuickSight setup.

The CSV export script works with both deployment configurations:
- **Automated analytics enabled**: Script works with the automatically created resources
- **Automated analytics disabled**: Script works with manual Athena setup or can export directly from S3

See the script documentation for usage instructions.

## Partition Management and Automation

### Why Partition Discovery is Required

The Case Insights solution stores data in S3 using a **partitioned structure**:
```
s3://s3-<unique-identifier>-caseprocessed/
├── account_number=123456789012/
│   ├── case_number=12345678901/
│   │   └── data.json
│   └── case_number=12345678902/
│       └── data.json
└── account_number=987654321098/
    └── case_number=98765432101/
        └── data.json
```

**The Problem**: When new cases are processed and stored in S3, Athena doesn't automatically know about these new partitions. This means:
- New case data won't appear in query results
- Queries may return incomplete data
- Performance may be suboptimal

**The Solution**: Run `MSCK REPAIR TABLE` to discover new partitions, or set up automation to do this automatically.

### Manual Partition Discovery

Should cases not be discovered by the crawler you can run a manual repair to discover the partitions:

```sql
MSCK REPAIR TABLE case_insights_<your-unique-identifier>.case_summary;
```

## Troubleshooting

### Common Issues

**Error: "Illegal character in authority"** (Manual setup only)
- This error occurs when you haven't replaced `<your-unique-identifier>` with your actual UniqueIdentifier value in the LOCATION clause.
- Make sure to use the same UniqueIdentifier value you used when deploying the CloudFormation stack.
- The S3 bucket name should not contain angle brackets (`<` or `>`).

**Error: "Table not found" or "No partitions found"**
- **Automated setup**: Verify the database and table names from CloudFormation outputs are correct
- **Manual setup**: Run `MSCK REPAIR TABLE case_insights.case_summary;` to discover partitions
- Ensure that the S3 bucket exists and contains data in the expected partition structure: `account_number=123456789/case_number=12345678/data.json`
- Check that your Lambda functions have successfully processed cases and stored data in S3.

**No data returned from queries**
- Verify that the case retrieval and analysis process has completed successfully.
- Check CloudWatch Logs for any errors in the Lambda functions.
- Ensure that support cases exist in your AWS accounts and have been processed by the system.

## Example Queries

**Note:** The following queries use `case_insights.case_summary` which is the manual setup table name. If you used automated setup (`EnableAnalytics=true`), replace `case_insights` with your actual database name from the CloudFormation outputs.

### 1. Count Cases by RCA Category

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

### 2. Count Cases by Lifecycle Category

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

### 3. Cases by Service and RCA Category

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

### 4. Cases by Account and RCA Category

```sql
SELECT
  account_number,
  RCA_Category,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  RCA_Category IS NOT NULL
GROUP BY
  account_number,
  RCA_Category
ORDER BY
  account_number,
  case_count DESC;
```

### 5. Cases by Month and RCA Category

```sql
SELECT
  DATE_FORMAT(from_iso8601_timestamp(timeCreated), '%Y-%m') as month,
  RCA_Category,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  RCA_Category IS NOT NULL
GROUP BY
  DATE_FORMAT(from_iso8601_timestamp(timeCreated), '%Y-%m'),
  RCA_Category
ORDER BY
  month,
  case_count DESC;
```

### 6. Cases by Severity and RCA Category

```sql
SELECT
  severityCode,
  RCA_Category,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  RCA_Category IS NOT NULL
GROUP BY
  severityCode,
  RCA_Category
ORDER BY
  severityCode,
  case_count DESC;
```

### 7. Cases with Specific RCA Category

```sql
SELECT
  account_number,
  case_number,
  subject,
  serviceCode,
  categoryCode,
  severityCode,
  submittedBy,
  timeCreated,
  RCA_Category,
  RCA_Reason,
  Lifecycle_Category,
  Lifecycle_Reason
FROM
  case_insights.case_summary
WHERE
  RCA_Category = 'Throttling'
  AND timeCreated BETWEEN '2023-01-01' AND '2023-12-31'
ORDER BY
  timeCreated DESC;
```

### 8. Cases with Specific Lifecycle Category

```sql
SELECT
  account_number,
  case_number,
  subject,
  serviceCode,
  categoryCode,
  severityCode,
  submittedBy,
  timeCreated,
  RCA_Category,
  RCA_Reason,
  Lifecycle_Category,
  Lifecycle_Reason
FROM
  case_insights.case_summary
WHERE
  Lifecycle_Category = 'Load Testing'
  AND timeCreated BETWEEN '2023-01-01' AND '2023-12-31'
ORDER BY
  timeCreated DESC;
```

### 9. Top Services with Issues

```sql
SELECT
  serviceCode,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  timeCreated BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY
  serviceCode
ORDER BY
  case_count DESC
LIMIT 10;
```

### 10. Trend Analysis by Week

```sql
SELECT
  DATE_FORMAT(from_iso8601_timestamp(timeCreated), '%Y-%m-%d') as week_start,
  WEEK(from_iso8601_timestamp(timeCreated)) as week_number,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  timeCreated BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY
  DATE_FORMAT(from_iso8601_timestamp(timeCreated), '%Y-%m-%d'),
  WEEK(from_iso8601_timestamp(timeCreated))
ORDER BY
  week_start;
```

**Alternative using date truncation to Monday of each week:**
```sql
SELECT
  DATE_FORMAT(
    DATE_ADD('day', 
      -(DAY_OF_WEEK(from_iso8601_timestamp(timeCreated)) - 2), 
      from_iso8601_timestamp(timeCreated)
    ), '%Y-%m-%d'
  ) as week_start,
  COUNT(*) as case_count
FROM
  case_insights.case_summary
WHERE
  timeCreated BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY
  DATE_FORMAT(
    DATE_ADD('day', 
      -(DAY_OF_WEEK(from_iso8601_timestamp(timeCreated)) - 2), 
      from_iso8601_timestamp(timeCreated)
    ), '%Y-%m-%d'
  )
ORDER BY
  week_start;
```