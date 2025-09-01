# Support Case Insights - Resources Created

This document provides a comprehensive list of all AWS resources created by the CloudFormation templates in the Support Case Insights solution.

## Main CloudFormation Template (case-insights.yaml)

### S3 Buckets

| Resource Name | Type | Description |
|---------------|------|-------------|
| `s3-${UniqueIdentifier}-accountlist` | S3 Bucket | Stores the list of active AWS accounts |
| `s3-${UniqueIdentifier}-caseraw` | S3 Bucket | Stores raw support case data during processing |
| `s3-${UniqueIdentifier}-caseprocessed` | S3 Bucket | Stores processed case data with AI-generated insights |
| `s3-${UniqueIdentifier}-athena-results` | S3 Bucket | Stores Athena query results (created only when EnableAnalytics=true) |

### SQS Queues

| Resource Name | Type | Description |
|---------------|------|-------------|
| SQS-ActiveAccounts | SQS Queue | Queue of active AWS accounts for case retrieval |
| SQS-ActiveAccounts-DLQ | SQS Queue (Dead Letter) | Dead letter queue for ActiveAccounts |
| SQS-CaseAnnotation | SQS Queue | Queue of cases for annotation retrieval |
| SQS-CaseAnnotation-DLQ | SQS Queue (Dead Letter) | Dead letter queue for CaseAnnotation |
| SQS-CaseSummary | SQS Queue | Queue of cases for AI analysis |
| SQS-CaseSummary-DLQ | SQS Queue (Dead Letter) | Dead letter queue for CaseSummary |

### IAM Roles

| Resource Name | Type | Description |
|---------------|------|-------------|
| CaseInsights-LambdaExecutionRole-${UniqueIdentifier} | IAM Role | Execution role for Lambda functions with permissions for S3, SQS, STS, and Organizations |
| CaseInsights-StartStepFunctionRole-${UniqueIdentifier} | IAM Role | Execution role for StartStepFunction Lambda with permissions to start Step Function executions |
| CaseInsights-StepFunctionExecutionRole-${UniqueIdentifier} | IAM Role | Execution role for Step Functions with permissions to invoke Lambda functions |
| CaseInsights-BedrockExecutionRole-${UniqueIdentifier} | IAM Role | Execution role for Lambda functions that use Bedrock with permissions for S3, SQS, and Bedrock |
| CaseInsights-CaseCleanupRole-${UniqueIdentifier} | IAM Role | Execution role for case cleanup Lambda with permissions for S3 operations and CloudWatch metrics |
| CaseInsights-GlueServiceRole-${UniqueIdentifier} | IAM Role | Service role for Glue crawler with permissions to access S3 and update Glue Data Catalog (created only when EnableAnalytics=true) |
| ApiGatewayCloudWatchLogsRole | IAM Role | Service role for API Gateway to write access logs to CloudWatch Logs (created only in MCP server template) |

### Lambda Functions

| Resource Name | Type | Description |
|---------------|------|-------------|
| Lambda-AccountLookup-${UniqueIdentifier} | Lambda Function | Retrieves active AWS accounts from an organization |
| Lambda-AccountReader-${UniqueIdentifier} | Lambda Function | Reads account list and sends messages to SQS |
| Lambda-CaseRetrieval-${UniqueIdentifier} | Lambda Function | Retrieves support cases for an account |
| Lambda-CaseAnnotation-${UniqueIdentifier} | Lambda Function | Retrieves case communications |
| Lambda-CaseCleanup-${UniqueIdentifier} | Lambda Function | Removes incomplete cases from S3 storage |
| Lambda-StartStepFunction-${UniqueIdentifier} | Lambda Function | Starts the AI analysis step function |
| Step-CaseSummary-${UniqueIdentifier} | Lambda Function | Generates case summary using AI |
| Step-RCAAnalysis-${UniqueIdentifier} | Lambda Function | Categorizes root cause using AI |
| Step-LifecycleAnalysis-${UniqueIdentifier} | Lambda Function | Identifies lifecycle improvement opportunities using AI |
| Step-UpdateCaseMetadata-${UniqueIdentifier} | Lambda Function | Updates case metadata with AI insights |

**Note:** All Lambda functions are configured with `ReservedConcurrentExecutions: 10` to prevent any single function from consuming all available concurrent executions in the AWS account. This reserves 100 total concurrent executions (10 functions × 10 each) out of the default 1000 account limit, leaving 900 available for other functions.

### Lambda Event Source Mappings

| Resource Name | Type | Description |
|---------------|------|-------------|
| CaseRetrievalEventSourceMapping | Lambda Event Source Mapping | Connects ActiveAccountsQueue to CaseRetrievalFunction |
| CaseAnnotationEventSourceMapping | Lambda Event Source Mapping | Connects CaseAnnotationQueue to CaseAnnotationFunction |
| StartStepFunctionEventSourceMapping | Lambda Event Source Mapping | Connects CaseSummaryQueue to StartStepFunctionFunction |

### Lambda Permissions

| Resource Name | Type | Description |
|---------------|------|-------------|
| S3InvokeLambdaPermission | Lambda Permission | Allows S3 to invoke AccountReaderFunction |
| DailyAccountLookupPermission | Lambda Permission | Allows CloudWatch Events to invoke AccountLookupFunction |

### Step Functions

| Resource Name | Type | Description |
|---------------|------|-------------|
| CaseAnalysis-${UniqueIdentifier} | Step Function | Orchestrates the AI analysis workflow |

### CloudWatch Events

| Resource Name | Type | Description |
|---------------|------|-------------|
| DailyAccountLookup-${UniqueIdentifier} | CloudWatch Events Rule | Triggers the AccountLookup Lambda function daily |
| DailyCaseCleanup-${UniqueIdentifier} | CloudWatch Events Rule | Triggers the CaseCleanup Lambda function daily at 8:00 AM UTC |

### CloudWatch Dashboard

| Resource Name | Type | Description |
|---------------|------|-------------|
| CaseInsights-${UniqueIdentifier} | CloudWatch Dashboard | Monitoring dashboard for the Support Case Insights solution |

### CloudWatch Alarms

| Resource Name | Type | Description |
|---------------|------|-------------|
| CaseInsights-LambdaErrors-${UniqueIdentifier} | CloudWatch Alarm | Alarm when Lambda functions have errors |
| CaseInsights-StepFunctionFailures-${UniqueIdentifier} | CloudWatch Alarm | Alarm when Step Functions fail |
| CaseInsights-DLQMessages-${UniqueIdentifier} | CloudWatch Alarm | Alarm when messages are sent to DLQ |
| CaseInsights-CleanupErrors-${UniqueIdentifier} | CloudWatch Alarm | Alarm when case cleanup encounters errors |

## Analytics Resources (Created when EnableAnalytics=true)

The following resources are created only when the `EnableAnalytics` parameter is set to `true` during deployment:

### AWS Glue Resources

| Resource Name | Type | Description |
|---------------|------|-------------|
| case_insights_${UniqueIdentifier} | Glue Database | Database for storing case insights metadata |
| case_summary | Glue Table | External table definition for querying case data in S3 |
| CaseInsights-GlueServiceRole-${UniqueIdentifier} | IAM Role | Service role for Glue crawler with permissions to access S3 and update Glue Data Catalog |
| case-insights-partition-crawler-${UniqueIdentifier} | Glue Crawler | Automatically discovers new partitions in S3 data, runs daily at 9 AM UTC |

### Amazon Athena Resources

| Resource Name | Type | Description |
|---------------|------|-------------|
| CaseInsights-${UniqueIdentifier} | Athena WorkGroup | Dedicated workgroup for case insights queries with automatic result location |

### Additional IAM Roles (Analytics)

No additional IAM roles are created for analytics. Users must have appropriate permissions to execute Athena queries.  See installation document for examples.

### S3 Bucket Lifecycle Policies

The Athena query results bucket (`s3-${UniqueIdentifier}-athena-results`) includes automatic lifecycle management:
- Query results are automatically deleted after 30 days
- Incomplete multipart uploads are cleaned up after 7 days

## Child Account CloudFormation Template (child-account-role.yaml)

### IAM Roles

| Resource Name | Type | Description |
|---------------|------|-------------|
| Support-Case-Analysis-Role | IAM Role | Role in child accounts that allows the management account to access support cases |

## Resource Naming Convention

Most resources include a unique identifier parameter (`${UniqueIdentifier}`) to ensure resource names are unique across deployments. This parameter is provided during the CloudFormation stack creation.

## Resource Dependencies

The solution has the following key dependencies:

1. **S3 to Lambda**: The AccountListBucket triggers the AccountReaderFunction when a new account list is uploaded
2. **SQS to Lambda**: The SQS queues trigger their respective Lambda functions
3. **Lambda to Step Function**: The StartStepFunctionFunction starts the CaseAnalysisStateMachine
4. **Step Function to Lambda**: The Step Function executes the AI analysis Lambda functions in sequence
5. **CloudWatch Events to Lambda**: The DailyAccountLookupRule triggers the AccountLookupFunction daily

## Resource Permissions

The solution uses five main IAM roles:

1. **LambdaExecutionRole**: For general Lambda functions that interact with S3, SQS, and assume roles in child accounts
2. **StartStepFunctionRole**: For the StartStepFunction Lambda function to start Step Function executions
3. **StepFunctionExecutionRole**: For the Step Function to invoke Lambda functions
4. **BedrockExecutionRole**: For Lambda functions that use Amazon Bedrock for AI analysis
5. **CaseCleanupRole**: For the case cleanup Lambda function to manage S3 objects and publish metrics
6. **ApiGatewayCloudWatchLogsRole**: For API Gateway to write access logs to CloudWatch Logs (MCP server only)
7. **Support-Case-Analysis-Role**: In child accounts to allow the management account to access support cases

## Resource Cleanup

When you delete the CloudFormation stack, most resources will be automatically deleted. However, the S3 buckets may not be deleted if they contain objects. You'll need to empty the buckets manually before deleting the stack.