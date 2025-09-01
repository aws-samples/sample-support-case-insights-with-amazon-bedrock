# IAM Roles and Permissions

This document provides detailed information about the IAM roles and permissions used by the Support Case Insights solution.

## Overview

The Support Case Insights solution uses several IAM roles to ensure the principle of least privilege is followed. Each role is granted only the permissions necessary to perform its specific functions.

## Roles Created by CloudFormation

### 1. Lambda Execution Role

**Name:** `CaseInsights-LambdaExecutionRole-${UniqueIdentifier}`

**Purpose:** This role is used by Lambda functions that need to access S3, SQS, and assume roles in other accounts.

**Permissions:**

- **Managed Policies:**
  - `AWSLambdaBasicExecutionRole`: Allows Lambda functions to write logs to CloudWatch Logs

- **S3 Access:**
  - `s3:GetObject`
  - `s3:PutObject`
  - `s3:ListBucket`
  - `s3:HeadObject`
  - Resources:
    - `arn:aws:s3:::s3-${UniqueIdentifier}-accountlist`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-accountlist/*`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseraw`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseraw/*`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed/*`

- **SQS Access:**
  - `sqs:SendMessage`
  - `sqs:ReceiveMessage`
  - `sqs:DeleteMessage`
  - `sqs:GetQueueAttributes`
  - Resources:
    - `SQS-ActiveAccounts`
    - `SQS-CaseAnnotation`
    - `SQS-CaseSummary`

- **STS Assume Role:**
  - `sts:AssumeRole`
  - Resources:
    - `arn:aws:iam::*:role/Support-Case-Analysis-Role`

- **Organizations Access:**
  - `organizations:ListAccounts`
  - Resources: `*`

### 2. Start Step Function Execution Role

**Name:** `CaseInsights-StartStepFunctionRole-${UniqueIdentifier}`

**Purpose:** This role is used by the StartStepFunction Lambda function to start Step Function executions.

**Permissions:**

- **Managed Policies:**
  - `AWSLambdaBasicExecutionRole`: Allows Lambda functions to write logs to CloudWatch Logs

- **Step Function Access:**
  - `states:StartExecution`
  - `states:DescribeExecution`
  - `states:ListExecutions`
  - Resources:
    - `arn:aws:states:${AWS::Region}:${AWS::AccountId}:stateMachine:CaseAnalysis-${UniqueIdentifier}`

- **SQS Access:**
  - `sqs:ReceiveMessage`
  - `sqs:DeleteMessage`
  - `sqs:GetQueueAttributes`
  - Resources:
    - `SQS-CaseSummary`

### 3. Step Function Execution Role

**Name:** `CaseInsights-StepFunctionExecutionRole-${UniqueIdentifier}`

**Purpose:** This role is used by the Step Function to invoke Lambda functions.

**Permissions:**

- **Lambda Invoke:**
  - `lambda:InvokeFunction`
  - Resources:
    - `Step-CaseSummary`
    - `Step-RCAAnalysis`
    - `Step-LifecycleAnalysis`
    - `Step-UpdateCaseMetadata`

### 4. Bedrock Execution Role

**Name:** `CaseInsights-BedrockExecutionRole-${UniqueIdentifier}`

**Purpose:** This role is used by Lambda functions that need to access Bedrock.

**Permissions:**

- **Managed Policies:**
  - `AWSLambdaBasicExecutionRole`: Allows Lambda functions to write logs to CloudWatch Logs

- **S3 Access:**
  - `s3:GetObject`
  - `s3:PutObject`
  - `s3:ListBucket`
  - `s3:HeadObject`
  - Resources:
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseraw`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseraw/*`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed/*`

- **SQS Access:**
  - `sqs:DeleteMessage`
  - Resources:
    - `SQS-CaseSummary`

- **Bedrock Access:**
  - `bedrock:InvokeModel`
  - Resources:
    - `arn:aws:bedrock:${AWS::Region}::foundation-model/${BedrockModelId}`

### 5. Case Cleanup Execution Role

**Name:** `CaseInsights-CaseCleanupRole-${UniqueIdentifier}`

**Purpose:** This role is used by the case cleanup Lambda function to remove incomplete cases and publish metrics.

**Permissions:**

- **Managed Policies:**
  - `AWSLambdaBasicExecutionRole`: Allows Lambda functions to write logs to CloudWatch Logs

- **S3 Access:**
  - `s3:ListBucket`
  - `s3:GetObject`
  - `s3:DeleteObject`
  - `s3:HeadObject`
  - Resources:
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseraw`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseraw/*`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed/*`

- **CloudWatch Metrics:**
  - `cloudwatch:PutMetricData`
  - Resources: `*`

### 6. API Gateway CloudWatch Logs Role

**Name:** `ApiGatewayCloudWatchLogsRole`

**Purpose:** This role allows API Gateway to write access logs to CloudWatch Logs. This is required for API Gateway access logging functionality.

**Permissions:**

- **Managed Policies:**
  - `AmazonAPIGatewayPushToCloudWatchLogs`: AWS managed policy that provides permissions for API Gateway to push logs to CloudWatch

**Trust Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### 7. Glue Service Role (Analytics Only)

**Name:** `CaseInsights-GlueServiceRole-${UniqueIdentifier}`

**Purpose:** This role is used by the Glue crawler to access S3 data and update the Glue Data Catalog. Only created when `EnableAnalytics=true`.

**Permissions:**

- **Managed Policies:**
  - `AWSGlueServiceRole`: Standard AWS managed policy for Glue service operations

- **S3 Access:**
  - `s3:GetObject`
  - `s3:ListBucket`
  - Resources:
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed`
    - `arn:aws:s3:::s3-${UniqueIdentifier}-caseprocessed/*`

**Trust Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Child Account Role

### Support Case Analysis Role

**Name:** `Support-Case-Analysis-Role`

**Purpose:** This role is assumed by the Lambda functions in the management account to access support cases in child accounts.

**Permissions:**

- **Support Case Access:**
  - `support:DescribeCases`
  - `support:DescribeCommunications`
  - Resources: `*`

**Trust Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ManagementAccountId}:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalOrgID": "${OrganizationId}"
        }
      }
    }
  ]
}
```

## Setting Up the Child Account Role

The `Support-Case-Analysis-Role` needs to be created in each child account that you want to analyze support cases for. This can be done using the provided CloudFormation template:

```bash
aws cloudformation deploy \
  --template-file cloudformation/child-account-role.yaml \
  --stack-name support-case-analysis-role \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ManagementAccountId=<your-management-account-id> \
    OrganizationId=<your-organization-id>
```

For large organizations, you can use AWS Organizations or StackSets to deploy this template to multiple accounts at once.

## Security Considerations

1. **Least Privilege:** The roles are designed to follow the principle of least privilege, granting only the permissions necessary for each function.

2. **Resource-Level Permissions:** Where possible, permissions are restricted to specific resources rather than using wildcard (`*`) permissions.

3. **Cross-Account Access:** The trust policy for the `Support-Case-Analysis-Role` includes a condition that restricts access to principals from the same AWS Organization, preventing unauthorized access from outside the organization.

4. **S3 Bucket Policies:** The S3 buckets have policies that restrict access to the account where they are created, preventing cross-account access except through the defined IAM roles.

5. **CloudWatch Logs:** All Lambda functions have permissions to write logs to CloudWatch Logs, enabling monitoring and troubleshooting.

## Troubleshooting Permission Issues

If you encounter permission issues, check the following:

1. **CloudTrail Logs:** Check CloudTrail logs for `AccessDenied` errors to identify the specific permission that is missing.

2. **IAM Policy Simulator:** Use the IAM Policy Simulator to test whether a specific action is allowed for a role.

3. **CloudWatch Logs:** Check the CloudWatch Logs for the Lambda functions to see detailed error messages.

4. **Trust Relationships:** Ensure that the trust relationships are correctly configured for cross-account access.

5. **Organization ID:** Verify that the AWS Organization ID is correctly specified in the trust policy for the `Support-Case-Analysis-Role`.