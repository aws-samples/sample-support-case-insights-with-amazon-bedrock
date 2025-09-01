# Support Case Insights - Logging and Troubleshooting Guide

This document explains how logging works in the Support Case Insights solution and provides guidance for troubleshooting common issues.

## Overview

The Support Case Insights solution uses AWS CloudWatch Logs to capture detailed information about the processing pipeline. Understanding the logging structure is crucial for monitoring the system and troubleshooting issues.

## Log Group Structure

### One Log Group Per Lambda Function

Each Lambda function in the solution creates its own CloudWatch Log Group:

| Lambda Function | Log Group Name |
|----------------|----------------|
| Account Lookup | `/aws/lambda/Lambda-AccountLookup-{UniqueIdentifier}` |
| Account Reader | `/aws/lambda/Lambda-AccountReader-{UniqueIdentifier}` |
| Case Retrieval | `/aws/lambda/Lambda-CaseRetrieval-{UniqueIdentifier}` |
| Case Annotation | `/aws/lambda/Lambda-CaseAnnotation-{UniqueIdentifier}` |
| Start Step Function | `/aws/lambda/Lambda-StartStepFunction-{UniqueIdentifier}` |
| Case Summary | `/aws/lambda/Step-CaseSummary-{UniqueIdentifier}` |
| RCA Analysis | `/aws/lambda/Step-RCAAnalysis-{UniqueIdentifier}` |
| Lifecycle Analysis | `/aws/lambda/Step-LifecycleAnalysis-{UniqueIdentifier}` |
| Update Case Metadata | `/aws/lambda/Step-UpdateCaseMetadata-{UniqueIdentifier}` |
| Case Cleanup | `/aws/lambda/Lambda-CaseCleanup-{UniqueIdentifier}` |

### MCP Server API Access Logs (Optional Component)

If you've deployed the optional MCP (Model Context Protocol) server, it creates additional access logs:

| Component | Log Group Name | Purpose |
|-----------|----------------|---------|
| MCP Server API Gateway | `/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}` | API access logs for security and debugging |
| MCP Lambda Function | `/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}` | MCP server application logs |

### Multiple Log Streams Per Log Group

Within each Log Group, AWS Lambda creates separate **Log Streams** for each execution:

```
/aws/lambda/Step-RCAAnalysis-255248/
├── 2025/01/25/[$LATEST]abc123def456  ← Case 1 execution
├── 2025/01/25/[$LATEST]xyz789uvw012  ← Case 2 execution
├── 2025/01/25/[$LATEST]mno345pqr678  ← Case 3 execution
└── 2025/01/25/[$LATEST]hij901klm234  ← Case 4 execution
```

**Important**: Each case is processed in a separate Lambda execution, creating its own log stream. This enables parallel processing but means you'll see multiple cases being processed "simultaneously" in the same Log Group.

## Understanding Log Entries

### Standard Lambda Log Format

Each Lambda execution follows this pattern:

```
START RequestId: 12345678-1234-1234-1234-123456789012 Version: $LATEST
[INFO] Processing account 123456789012
[INFO] Successfully processed 5 new cases for account 123456789012
END RequestId: 12345678-1234-1234-1234-123456789012
REPORT RequestId: 12345678-1234-1234-1234-123456789012 Duration: 2543.21 ms Billed Duration: 2544 ms Memory Size: 256 MB Max Memory Used: 89 MB
```

### Key Log Elements

- **START**: Beginning of Lambda execution with unique Request ID
- **INFO/ERROR/WARNING**: Application logs with severity levels
- **END**: Successful completion of Lambda execution
- **REPORT**: Performance metrics (duration, memory usage, billing)

### Request ID Tracking

Each Lambda execution has a unique Request ID that appears in all log entries for that execution. Use this to track a specific case through the processing pipeline.

## Processing Flow and Logging

### 1. Daily Account Discovery
**Function**: `Lambda-AccountLookup`
**Trigger**: CloudWatch Events (daily cron)
**Key Logs**:
```
[INFO] Retrieved 25 active AWS accounts
[INFO] Successfully stored account list to S3
```

### 2. Account Processing
**Function**: `Lambda-AccountReader`
**Trigger**: S3 ObjectCreated event
**Key Logs**:
```
[INFO] Processing S3 event for bucket/active_aws_accounts.json
[INFO] Processing 25 accounts from bucket/active_aws_accounts.json
[INFO] Sent message for account 123456789012 to SQS, message ID: abc-123
```

### 3. Case Retrieval
**Function**: `Lambda-CaseRetrieval`
**Trigger**: SQS message from ActiveAccountsQueue
**Key Logs**:
```
[INFO] Processing account 123456789012
[INFO] Assuming role Support-Case-Analysis-Role in account 123456789012
[INFO] Retrieved 15 support cases
[INFO] Case 12345678 already exists, skipping
[INFO] Processed new case 87654321 for account 123456789012
[INFO] Successfully processed 3 new cases for account 123456789012
```

### 4. Case Annotation
**Function**: `Lambda-CaseAnnotation`
**Trigger**: SQS message from CaseAnnotationQueue
**Key Logs**:
```
[INFO] Processing case 87654321 for account 123456789012
[INFO] Retrieved 8 communications for case 87654321
[INFO] Successfully processed case 87654321 for account 123456789012
```

### 5. AI Analysis Pipeline
**Function**: `Lambda-StartStepFunction`
**Trigger**: SQS message from CaseSummaryQueue
**Key Logs**:
```
[INFO] Starting Step Function execution for bucket/account_number=123456789012/case_number=87654321
[INFO] Step Function execution started: arn:aws:states:us-east-1:123456789012:execution:CaseAnalysis-255248:abc-123
```

#### Step Function Logs

**Case Summary**:
```
[INFO] Processing file path: bucket/account_number=123456789012/case_number=87654321
[INFO] Invoking Bedrock model anthropic.claude-3-5-sonnet-20240620-v1:0 with max tokens 2000
[INFO] Generated summary of length 1247
```

**RCA Analysis**:
```
[INFO] Processing case summary for bucket/account_number=123456789012/case_number=87654321
[INFO] Invoking Bedrock model anthropic.claude-3-5-sonnet-20240620-v1:0 with max tokens 2000
[INFO] Generated RCA analysis of length 456
```

**Lifecycle Analysis**:
```
[INFO] Processing case summary for bucket/account_number=123456789012/case_number=87654321
[INFO] Invoking Bedrock model anthropic.claude-3-5-sonnet-20240620-v1:0 with max tokens 2000
[INFO] Generated lifecycle analysis of length 523
```

**Update Metadata**:
```
[INFO] Updating metadata for bucket/account_number=123456789012/case_number=87654321
[INFO] Updated metadata for bucket/account_number=123456789012/case_number=87654321
```

### 6. Case Cleanup
**Function**: `Lambda-CaseCleanup`
**Trigger**: CloudWatch Events (daily at 8:00 AM UTC)
**Key Logs**:
```
[INFO] Starting case cleanup for raw bucket s3-255248-caseraw and processed bucket s3-255248-caseprocessed
[INFO] Found 25 account folders
[INFO] Will process 23 accounts with 150 total cases
[INFO] Found incomplete case 87654321 in account 123456789012
[INFO] Successfully deleted 3 objects for case 87654321 in account 123456789012
[INFO] === CLEANUP SUMMARY (LIVE) ===
[INFO] Duration: 45.23 seconds
[INFO] Accounts processed: 23
[INFO] Cases scanned: 150
[INFO] Cases removed: 5
[INFO] Errors encountered: 0
```

## Common Log Patterns and What They Mean

### Success Patterns

✅ **Normal Processing**:
```
[INFO] Successfully processed 3 new cases for account 123456789012
[INFO] Generated summary of length 1247
[INFO] Updated metadata for bucket/account_number=123456789012/case_number=87654321
```

✅ **No New Cases** (Normal):
```
[INFO] No support cases found for account 123456789012
[INFO] Successfully processed 0 new cases for account 123456789012
```

✅ **Successful Cleanup** (Normal):
```
[INFO] No incomplete cases found - nothing to clean up
[INFO] Successfully cleaned up 3 incomplete cases
[INFO] No incomplete cases found - data quality is good!
```

### Warning Patterns

⚠️ **Access Issues** (Expected for some accounts):
```
[WARNING] Access denied when assuming role in account 123456789012. The role may not exist or you may not have permission to assume it.
[WARNING] Support API access issue for account: SubscriptionRequiredException. This is expected for accounts without Business or Enterprise Support.
```

### Error Patterns

❌ **Configuration Issues**:
```
[ERROR] Missing accountId in SQS message
[ERROR] Failed to assume role arn:aws:iam::123456789012:role/Support-Case-Analysis-Role: AccessDenied
[ERROR] Failed to retrieve support cases: SubscriptionRequiredException
```

❌ **AI Processing Issues**:
```
[ERROR] Failed to parse RCA response as JSON: Extra data
[ERROR] Failed to invoke Bedrock model: AccessDeniedException
[ERROR] Failed to load template from /opt/templates/rca-template.txt: No such file or directory
```

❌ **Cleanup Issues**:
```
[ERROR] Failed to delete case folder account_number=123456789012/case_number=87654321/: AccessDenied
[ERROR] Failed to list account folders: NoSuchBucket
[WARNING] Found 1500 incomplete cases, but limiting to 1000 per run
```

## Troubleshooting Guide

### 1. No Cases Being Processed

**Check**: Account Lookup logs
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/Lambda-AccountLookup-{UniqueIdentifier}" \
  --start-time $(date -d "1 day ago" +%s)000
```

**Look for**:
- "Retrieved X active AWS accounts"
- "Successfully stored account list to S3"

### 2. Cases Not Being Retrieved

**Check**: Case Retrieval logs
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/Lambda-CaseRetrieval-{UniqueIdentifier}" \
  --filter-pattern "ERROR" \
  --start-time $(date -d "1 hour ago" +%s)000
```

**Common Issues**:
- Role assumption failures
- Support API access issues
- Missing Business/Enterprise Support

### 3. AI Analysis Failures

**Check**: Step Function logs
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/Step-RCAAnalysis-{UniqueIdentifier}" \
  --filter-pattern "ERROR" \
  --start-time $(date -d "1 hour ago" +%s)000
```

**Common Issues**:
- JSON parsing errors
- Bedrock access denied
- Template loading failures

### 4. Step Function Execution Issues

**Check**: Step Function execution history
```bash
aws stepfunctions list-executions \
  --state-machine-arn "arn:aws:states:{region}:{account}:stateMachine:CaseAnalysis-{UniqueIdentifier}" \
  --status-filter FAILED
```

### 5. Case Cleanup Issues

**Check**: Case Cleanup logs
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/Lambda-CaseCleanup-{UniqueIdentifier}" \
  --filter-pattern "ERROR" \
  --start-time $(date -d "1 day ago" +%s)000
```

**Common Issues**:
- S3 access denied errors
- Too many incomplete cases (hitting max deletion limit)
- Bucket not found or misconfigured

## Monitoring Best Practices

### 1. Set Up CloudWatch Alarms

The solution includes pre-configured alarms for:
- Lambda function errors
- Step Function failures
- Dead Letter Queue messages

### 2. Use CloudWatch Insights

Query across multiple log groups:
```sql
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

### 3. Monitor Key Metrics

- **Lambda Invocations**: Track processing volume
- **Lambda Errors**: Identify failing functions
- **Lambda Duration**: Monitor performance
- **SQS Queue Depth**: Check for backlogs
- **Step Function Executions**: Monitor AI analysis pipeline

### 4. Regular Log Review

- Check for access denied errors (may indicate missing roles)
- Monitor Bedrock usage and costs
- Review case processing volumes
- Identify accounts without support cases

## Log Retention

By default, CloudWatch Logs are retained indefinitely. Consider setting retention policies:

```bash
aws logs put-retention-policy \
  --log-group-name "/aws/lambda/Lambda-CaseRetrieval-{UniqueIdentifier}" \
  --retention-in-days 30
```

## Getting Help

If you encounter issues not covered in this guide:

1. **Check the specific error message** in the logs
2. **Verify IAM permissions** for the failing operation
3. **Check AWS service quotas** (especially for Bedrock)
4. **Review the CloudWatch Dashboard** for overall system health
5. **Consult AWS Support** for service-specific issues

## MCP Server Logging (Optional Component)

If you've deployed the optional MCP server, additional logging is available:

### API Gateway Access Logs

**Log Group**: `/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}`

**Purpose**: Complete audit trail of all API requests to the MCP server

**Log Format**: JSON structured logs containing:
```json
{
  "requestId": "12345-67890-abcdef",
  "timestamp": "25/Dec/2024:10:30:45 +0000",
  "httpMethod": "POST",
  "resourcePath": "/mcp",
  "status": "200",
  "responseTime": "1250",
  "clientIp": "192.168.1.100",
  "caller": "arn:aws:iam::123456789012:user/john",
  "user": "john",
  "error": ""
}
```

**Use Cases**:
- **Security monitoring**: Track who accessed the API and when
- **Performance analysis**: Monitor response times and identify slow queries
- **Debugging**: Troubleshoot API issues with detailed request information
- **Usage analytics**: Understand API usage patterns

### MCP Lambda Function Logs

**Log Group**: `/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}`

**Purpose**: Application-level logging for MCP server operations

**Common Log Patterns**:
```
[INFO] Executing tool: query_athena with query: SELECT COUNT(*) FROM case_summary
[INFO] Athena query execution started: 12345-67890-abcdef
[INFO] Query completed successfully, returning 150 rows
[INFO] Bedrock analysis completed for 200 case summaries
[ERROR] Athena query failed: InvalidQueryException
```

### Monitoring MCP Server

**Key metrics to monitor**:
- API request volume and response times
- Authentication failures (403 errors)
- Throttling events (429 errors)
- Athena query performance
- Bedrock usage and costs

**Troubleshooting MCP Issues**:

1. **Authentication Problems**:
   ```bash
   aws logs filter-log-events \
     --log-group-name "/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}" \
     --filter-pattern "{ $.status = 403 }"
   ```

2. **Performance Issues**:
   ```bash
   aws logs filter-log-events \
     --log-group-name "/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}" \
     --filter-pattern "{ $.responseTime > 5000 }"
   ```

3. **Application Errors**:
   ```bash
   aws logs filter-log-events \
     --log-group-name "/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}" \
     --filter-pattern "ERROR"
   ```

Remember: Each case is processed independently, so seeing multiple cases in the same Log Group is normal and indicates healthy parallel processing.