# Support Case Insights with Amazon Bedrock - Installation Guide

This guide walks you through deploying the Support Case Insights solution step by step.

## Deployment Permissions

Before deploying the Support Case Insights solution, ensure your IAM user or role has the following permissions. These permissions are required to create and delete the CloudFormation stack and all associated AWS resources.

### Required IAM Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "organizations:DescribeOrganization",
                "cloudformation:CreateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PassRole",
                "iam:GetRole",
                "iam:getRolePolicy",
                "iam:TagRole",
                "iam:UntagRole",
                "iam:CreatePolicy",
                "iam:DeletePolicy",
                "iam:GetPolicy",
                "iam:ListPolicyVersions",
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:PutFunctionConcurrency",
                "lambda:CreateEventSourceMapping",
                "lambda:DeleteEventSourceMapping",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:PublishLayerVersion",
                "lambda:DeleteLayerVersion",
                "lambda:GetFunction",
                "lambda:GetLayerVersion",
                "lambda:GetEventSourceMapping",
                "lambda:DeleteEventSourceMapping",
                "states:TagResource",
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:GetBucketPolicy",
                "s3:GetEncryptionConfiguration",
                "s3:GetBucketNotification",
                "s3:GetBucketTagging",
                "s3:GetBucketPublicAccessBlock",
                "s3:GetObject",
                "s3:PutLifecycleConfiguration",
                "s3:PutBucketPolicy",
                "s3:PutBucketVersioning",
                "s3:DeleteBucketPolicy",
                "s3:PutBucketNotification",
                "s3:PutBucketPublicAccessBlock",
                "s3:PutEncryptionConfiguration",
                "s3:PutBucketTagging",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListAllMyBuckets",
                "sqs:CreateQueue",
                "sqs:DeleteQueue",
                "sqs:getqueueattributes",
                "events:PutRule",
                "events:DescribeRule",
                "events:DeleteRule",
                "events:PutTargets",
                "events:RemoveTargets",
                "events:TagResource",
                "events:UntagResource",
                "states:CreateStateMachine",
                "states:DeleteStateMachine",
                "cloudwatch:PutMetricAlarm",
                "cloudwatch:DeleteAlarms",
                "cloudwatch:PutDashboard",
                "cloudwatch:DeleteDashboards",
                "logs:CreateLogStream",
                "logs:DeleteLogStream",
                "logs:DeleteLogGroup",
                "logs:CreateLogGroup",
                "logs:PutRetentionPolicy",
                "logs:DeleteRetentionPolicy",
                "logs:DescribeLogGroups",
                "glue:CreateCrawler",
                "glue:CreateTable",
                "glue:DeleteTable",
                "glue:DeleteCrawler",
                "glue:StopCrawler",
                "glue:CreateDatabase",
                "glue:DeleteDatabase",
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "athena:CreateWorkGroup",
                "athena:DeleteWorkGroup",
                "athena:GetWorkGroup",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel",
                "bedrock:InvokeModel",
                "aws-marketplace:ViewSubscriptions",
                "apigateway:POST",
                "apigateway:GET",
                "apigateway:PUT",
                "apigateway:DELETE",
                "apigateway:PATCH"
            ],
            "Resource": "*"
        }
    ]
}
```

### Security Considerations

- **Principle of Least Privilege**: This policy includes all permissions observed during CloudFormation stack deployment and deletion operations
- **Resource Scoping**: Service roles created by the CF template are scoped to least privilage.  See security.md for additional information.  The above policy is more permissive but could be restricted also for a production setting.

NOTE:  Ensure that you run this in your development environment first, do not run this directly in production without testing.  This solution is only intended for use in companies that utilise Organizations.  The Lambda functions query these APIs so if you're not using this functionality it is not recommended that you implement this solution.

## Security Architecture Decisions

This solution makes specific architectural choices that prioritize operational simplicity while maintaining security:


**S3 Access Logging:** S3 access logging is not enabled by default to reduce costs and operational overhead. All buckets use strong IAM controls and have public access blocked. Organizations requiring detailed access auditing can enable logging post-deployment or update the CF template.  

**MCP Server Security:** The optional MCP server deployment creates a publicly accessible API Gateway endpoint with IAM authentication, throttling limits (5 requests/second, 15 burst), and comprehensive access logging to CloudWatch. While IAM provides access control, AWS WAF is not included in the base deployment to reduce complexity. Organizations with strict security requirements should consider adding WAF protection for additional defense against web-based attacks.

**Encryption Configuration:** The solution uses AWS-managed encryption for cost optimization and operational simplicity:
- **S3 Buckets**: Server-side encryption with AES-256 (AWS-managed keys)
- **SQS Queues**: Default SQS-managed encryption (AWS-managed keys)
- **Data in Transit**: HTTPS/TLS for all AWS service communications

Organizations requiring customer-managed KMS keys can modify the CloudFormation template post-deployment to use custom KMS keys for enhanced key management control.

## Prerequisites

Before you begin, ensure you have:

- **AWS CLI** installed and configured with appropriate permissions
- **Python 3.9+** and pip installed
- **Access to AWS Organization** management account - This solution is intended to be installed in the management account.
- **Bedrock access** in your chosen region (check model availability)

### Required Python Libraries

Python3 should be installed.  Install the required Python packages for the packaging scripts:

```bash
pip install pyyaml boto3 pandas
```

Or if you prefer using pip3:
```bash
pip3 install pyyaml boto3 pandas
```

### Required AWS Permissions

See Deployment Permissions section at the top.  

**Additional for QuickSight**: If you plan to use QuickSight for data visualization, ensure your user has QuickSight admin permissions to configure data sources and manage S3 access during the manual setup process.

## Step 1: Enable Amazon Bedrock Models

**⚠️ CRITICAL**: The solution will not work without enabling Bedrock models. This must be done before deployment.

### Required Permissions for Bedrock Model Access

Your IAM user or role needs the following permission to enable Bedrock models:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel",
                "bedrock:InvokeModel",
                "aws-marketplace:ViewSubscriptions"
            ],
            "Resource": "*"
        }
    ]
}
```

**Key Permission**: `aws-marketplace:ViewSubscriptions` is required to access and enable Bedrock foundation models through the AWS console.

### 1.1 Enable Model Access

1. **Go to Amazon Bedrock Console**:
   ```
   https://console.aws.amazon.com/bedrock/home?region=<your-region>#/modelaccess
   ```

2. **Request Model Access**:
   - Click **"Manage model access"** or **"Model access"** in the left navigation
   - Find **"Anthropic Claude"** models in the list
   - Select **"Claude 3.5 Haiku"** (recommended default)
   - Optionally select **"Claude 3.5 Sonnet"** for higher quality analysis
   - Click **"Request model access"** or **"Save changes"**

3. **Wait for Approval**:
   - Most models are **instantly available**
   - Some may require a brief review process
   - Status will show **"Access granted"** when ready

### 1.2 Verify Model Access

Confirm your models are enabled:

```bash
# List available Bedrock models in your region
aws bedrock list-foundation-models --region <your-region> \
  --query 'modelSummaries[?contains(modelId, `anthropic`)].[modelId,modelName]' \
  --output table
```

**Expected output should include:**
```
|  anthropic.claude-3-5-haiku-20241022-v1:0     |  Claude 3.5 Haiku     |
|  anthropic.claude-3-5-sonnet-20240620-v1:0  |  Claude 3.5 Sonnet  |
```

### 1.3 Troubleshooting Model Access

**Common Issues:**

**"Access denied" errors:**
- Ensure you're in a [Bedrock-supported region](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html#bedrock-regions)
- Verify model access is granted in the Bedrock console
- Check your IAM permissions include:
  - `bedrock:InvokeModel`
  - `bedrock:ListFoundationModels`
  - `aws-marketplace:ViewSubscriptions` (required for model access page)

**"Model not found" errors:**
- Verify the exact model ID using `list-foundation-models`
- Some model IDs may vary by region
- Ensure you're using the correct model ID format

**"Throttling" errors:**
- Bedrock has default quotas that may need adjustment
- Request quota increases in the [Service Quotas console](https://console.aws.amazon.com/servicequotas/)

**Cannot access Bedrock console:**
- Verify you have the `aws-marketplace:ViewSubscriptions` permission
- This permission is required to view and enable foundation models
- Contact your AWS administrator if you don't have marketplace permissions

### Tested Bedrock Models

The solution has been tested with these Anthropic Claude models:

| Model | Model ID | Performance | Cost | Notes |
|-------|----------|-------------|------|-------|
| **Claude 3.5 Haiku** ⭐ **DEFAULT** | `anthropic.claude-3-5-haiku-20241022-v1:0` | Fast | Low | Recommended for cost efficiency |
| **Claude 3.5 Sonnet** | `anthropic.claude-3-5-sonnet-20240620-v1:0` | High Quality | Higher | Best analysis quality |

## Step 2: Package Lambda Functions

### 2.1 Clone the Repository
```bash
git clone https://github.com/aws-samples/aws-case-insights.git
cd aws-case-insights
```

### 2.2 Choose Your Identifiers

First, choose your unique identifiers that will be used throughout the deployment:

- **Unique Identifier**: A short identifier added to all AWS resources (e.g., `255248125`, `Prod21124`).  Remember Cloudformation will be creating buckets so make sure it's unique enough.  If you would like to check before hand, see the resources.md file for what gets created and pre-check the bucket names.
- **Deployment Bucket**: Must start with `case-insights-deployment-` (e.g., `case-insights-deployment-<uniqueID>`)

**Example:**
- Unique Identifier: `255248125`
- Deployment Bucket: `case-insights-deployment-255248125`
- Region: `us-east-1`

This will create resources like:
- Lambda functions: `Lambda-CaseRetrieval-255248125`, `Step-CaseSummary-255248125`
- S3 buckets: `s3-255248125-caseraw`, `s3-255248125-caseprocessed`

### 2.3 Package Lambda Functions

Ensure you have AWS credentials sourced and setup in environment variables or you've run "aws configure" to load these.  The permissions must match those in "Deployment Permissions" section at the top.

**Option A: Automated Setup (Recommended)**
The Lambda packaging script will automatically create the bucket and then package your Lambda functions.  Any issues here and you've probably not installed the dependencies.
```bash
# Run the automated packaging script (creates bucket automatically)
chmod +x scripts/package-lambdas.sh
./scripts/package-lambdas.sh <your-deployment-bucket> <your-region>

# Update CloudFormation template with your bucket name
python3 scripts/update-bucket-name.py cloudformation/case-insights.yaml <your-deployment-bucket>
```

If the bucket already exists then it will just use the bucket.

**Option B: Manual Bucket Creation**
If doing this, ensure that you scope the permissions for the bucket to this account only and disable any public access.

```bash
# Create deployment bucket manually first
aws s3 mb s3://<your-deployment-bucket> --region <your-region>

# Then run the packaging script
chmod +x scripts/package-lambdas.sh
./scripts/package-lambdas.sh <your-deployment-bucket> <your-region>

# Update CloudFormation template
python3 scripts/update-bucket-name.py cloudformation/case-insights.yaml <your-deployment-bucket>
```

**Example:**
```bash
# Option A (recommended) - using identifiers from step 2.2
./scripts/package-lambdas.sh case-insights-deployment-255248125 us-east-1

python3 scripts/update-bucket-name.py cloudformation/case-insights.yaml case-insights-deployment-255248125
```

## Step 3: Understand the Processing Schedule

Before deploying, it's important to understand when the solution will run its automated processes:

### **Daily Processing Schedule (UTC)**

| Function | Time (UTC) | Purpose | Your Local Time |
|----------|------------|---------|-----------------|
| **Account Lookup** | 00:00 UTC (Midnight) | Retrieves active AWS accounts from your organization | [Calculate your time](https://www.timeanddate.com/worldclock/converter.html?iso=20240101T000000&p1=1440) |
| **Case Cleanup** | 08:00 UTC (8:00 AM) | Removes incomplete/failed cases from storage | [Calculate your time](https://www.timeanddate.com/worldclock/converter.html?iso=20240101T080000&p1=1440) |

### **Daily Processing Flow**
```
00:00 UTC - Account Lookup
├── Gets list of active accounts
├── Triggers case retrieval for each account
└── Case processing continues throughout the day

08:00 UTC - Case Cleanup  
├── Removes any failed/incomplete cases
├── Prepares for next day's processing
└── Publishes cleanup metrics
```
Only cases which haven't yet been processed are evaluated.  The Lambda functions lookup cases in the processing bucket to understand the stage they're at.  If processing is complete thenthis case is skipped.

### **Time Zone Examples**
- **00:00 UTC**: 7:00 PM EST (previous day), 1:00 AM CET, 9:00 AM JST
- **08:00 UTC**: 3:00 AM EST, 9:00 AM CET, 5:00 PM JST

### **What This Means**
- Processing starts automatically each day at midnight UTC
- Case retrieval and AI analysis happen throughout the day
- Any processing issues are cleaned up 8 hours later
- No manual intervention required for daily operations

**Note**: You can modify these schedules by updating the CloudFormation template's `ScheduleExpression` values if needed.  Just remember to allow enough time for the cases to be processed before running the cleanup.  This will vary from minutes to hours depending on your environment.  8hrs is a safe bet.

## Step 4: Deploy the Solution
 
There are two options to the solution please read each one before choosing.  One will deploy just the case analysis stack with the S3 buckets.  The second option (Analytics) will deploy Athena and a glue crawler so that you can build insights into the data you retrieve.  We've given both options as you may choose to ingest your case insights into a 3rd party BI tool.  For this option we've supplied a script /scripts/generate_csv_insights.py which will pull the data from the s3 buckets. This will produce a series of insights in CSV format that could be exported for visualisation on a nightly basis.

To simplify the deployment, if Athena isn't yet available within your organisation, you could consider deploying the base components with CSV export and updating the stack (instructions below) to enable Analytics and the MCP later.

NOTE:  The MCP component requires you to run the analytics option as it depends on Athena to pull the insights.

### 4.1 Upload CloudFormation Template
```bash
# Upload template to S3 (required - template is >51KB)
aws s3 cp cloudformation/case-insights-updated.yaml s3://<your-unique-deployment-bucket>/case-insights-updated.yaml
```

### 4.2 Find Your Organization ID

Before deploying, you'll need your AWS Organization ID. Use this command to retrieve it:

```bash
# Get your Organization ID
aws organizations describe-organization --query 'Organization.Id' --output text
```

**Example output:**
```
o-84p3hidev6
```

**Note**: This command must be run from the management account of your AWS Organization. If you get an error, ensure you're authenticated with the correct account and have the necessary permissions to access AWS Organizations.

#### **Option A: Basic Deployment (No Analytics)**
```bash
aws cloudformation create-stack \
  --template-url https://s3.amazonaws.com/<your-deployment-bucket>.case-insights-updated.yaml \
  --stack-name aws-case-insights \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <your-region> \
  --parameters \
  ParameterKey=UniqueIdentifier,ParameterValue=<your-unique-identifier> \
  ParameterKey=OrganizationId,ParameterValue=<your-org-id> \
  ParameterKey=DeploymentTimestamp,ParameterValue=$(date +%Y-%m-%d-%H-%M-%S)
```

**Example:**
```bash
# Using identifiers from step 2.2
aws cloudformation create-stack \
  --template-url https://s3.amazonaws.com/case-insights-deployment-255248125/case-insights-updated.yaml \
  --stack-name aws-case-insights \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --parameters \
  ParameterKey=UniqueIdentifier,ParameterValue=255248125 \
  ParameterKey=OrganizationId,ParameterValue=o-84p3hidev6 \
  ParameterKey=DeploymentTimestamp,ParameterValue=$(date +%Y-%m-%d-%H-%M-%S)
```

#### **Option B: Analytics-Enabled Deployment**
```bash
# Deploy with analytics (includes Athena query results bucket)
aws cloudformation create-stack \
  --template-url https://<your-deployment-bucket>.s3.<your-region>.amazonaws.com/case-insights-updated.yaml \
  --stack-name aws-case-insights \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <your-region> \
  --parameters \
  ParameterKey=UniqueIdentifier,ParameterValue=<your-unique-identifier> \
  ParameterKey=OrganizationId,ParameterValue=<your-org-id> \
  ParameterKey=EnableAnalytics,ParameterValue=true \
  ParameterKey=DeploymentTimestamp,ParameterValue=$(date +%Y-%m-%d-%H-%M-%S)
```

### 4.3 Monitor Deployment
```bash
# Check deployment status
aws cloudformation describe-stacks --stack-name aws-case-insights --query 'Stacks[0].StackStatus'

# Watch deployment progress
aws cloudformation describe-stack-events --stack-name aws-case-insights --query 'StackEvents[0:5].[Timestamp,ResourceStatus,ResourceType]' --output table
```

## Step 5: Set Up Cross-Account Access

Deploy the support role to each child account in your organization:

```bash
aws cloudformation create-stack \
  --template-body file://cloudformation/child-account-role.yaml \
  --stack-name support-case-analysis-role \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <your-region> \
  --parameters \
  ParameterKey=ManagementAccountId,ParameterValue=<ManagementAccountNumber> \
  ParameterKey=OrganizationId,ParameterValue=<your-org-id>
```

> **💡 Tip**: Deploy this to each account where you want to analyze support cases, without it you will see lots of errors in the CloudWatch logs of your case functions.

## Customization Options

### Change Bedrock Model
To use a different AI model (e.g., Claude 3.5 Sonnet for higher quality):

```bash
aws cloudformation update-stack \
  --template-url https://<your-unique-deployment-bucket>.s3.<your-region>.amazonaws.com/case-insights-updated.yaml \
  --stack-name aws-case-insights \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <your-region> \
  --parameters \
  ParameterKey=BedrockModelId,ParameterValue=anthropic.claude-3-5-sonnet-20240620-v1:0 \
  ParameterKey=DeploymentTimestamp,ParameterValue=$(date +%Y-%m-%d-%H-%M-%S)
```

### Add Analytics Later
```bash
# Update stack to enable analytics (includes Athena query results bucket)
aws cloudformation update-stack \
  --template-url https://<your-unique-deployment-bucket>.s3.<your-region>.amazonaws.com/case-insights-updated.yaml \
  --stack-name aws-case-insights \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <your-region> \
  --parameters \
  ParameterKey=EnableAnalytics,ParameterValue=true \
  ParameterKey=DeploymentTimestamp,ParameterValue=$(date +%Y-%m-%d-%H-%M-%S)
```

## Verification

### Check Deployment
```bash
# Verify Lambda functions
aws lambda list-functions --query 'Functions[?contains(FunctionName, `CaseInsights`) || contains(FunctionName, `Step-`)].FunctionName'

# Verify S3 buckets
aws s3 ls | grep -E "(accountlist|caseraw|caseprocessed)"

# Check SQS queues
aws sqs list-queues --query 'QueueUrls[?contains(@, `SQS-`)]'
```

### Test Analytics (if enabled)
```bash
# List Athena databases
aws athena list-databases --catalog-name AwsDataCatalog --query 'DatabaseList[?contains(Name, `case_insights`)].Name'

# Test query
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM case_insights_<your-identifier>.case_summary" \
  --work-group CaseInsights-<your-identifier>
```

## Troubleshooting

### Common Issues

**Lambda functions not found**: Check packaging script ran successfully
```bash
aws s3 ls s3://<your-unique-deployment-bucket>/
```

**Stack creation failed**: Check CloudFormation events
```bash
aws cloudformation describe-stack-events --stack-name aws-case-insights --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

**No cases processed**: Verify cross-account role deployment
```bash
aws sts assume-role --role-arn arn:aws:iam::<child-account>:role/Support-Case-Analysis-Role --role-session-name test
```

**Analytics not working**: Check CloudFormation stack outputs for resource names
```bash
aws cloudformation describe-stacks --stack-name aws-case-insights --query 'Stacks[0].Outputs'
```

## Next Steps

1. **Monitor the dashboard**: Check CloudWatch dashboard for processing metrics
2. **Analyze data**: Use Athena queries or CSV export to analyze case insights
3. **Set up QuickSight**: Follow the manual setup instructions below (if analytics enabled)
4. **Schedule cleanup**: The solution includes automatic cleanup of incomplete cases

For detailed usage instructions, see the [Usage Guide](usage.md).

For Athena queries and analytics, see the [Athena Guide](athena.md).

## Athena Query Permissions

**Important**: To execute Athena queries on your case insights data, you need appropriate IAM permissions. Athena ExecutionRoles are not currently supported in all AWS regions, so queries will use the credentials of the authenticated user.

### Required IAM Permissions for Athena Queries

Your IAM user or role must have the following permissions to query case insights data:

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
                "athena:GetQueryResultsStream",
                "athena:ListQueryExecutions",
                "athena:StartQueryExecution",
                "athena:StopQueryExecution",
                "athena:GetWorkGroup",
                "athena:ListWorkGroups"
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
                "glue:GetDatabases",
                "glue:GetTable",
                "glue:GetTables",
                "glue:GetPartition",
                "glue:GetPartitions"
            ],
            "Resource": [
                "arn:aws:glue:*:*:catalog",
                "arn:aws:glue:*:*:database/case_insights_<your-unique-identifier>",
                "arn:aws:glue:*:*:table/case_insights_<your-unique-identifier>/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:PutObject",
                "s3:DeleteObject"
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

**Replace `<your-unique-identifier>`** with the actual UniqueIdentifier value you used when deploying the CloudFormation stack.


## Manual QuickSight Setup (Optional)

If you deployed with `EnableAnalytics=true`, you can set up Amazon QuickSight for data visualization. QuickSight requires manual configuration as it involves account-level settings and permissions.  Quicksight will create the necessary service linked role for itself and will update that linked role with permissions to Athena as you enable that functionality below.  See https://docs.aws.amazon.com/quicksight/latest/user/iam-policy-examples.html#security_iam_conosole-administration for example permissions for enabling quicksight.

### Prerequisites

- Support Case Insights deployed with `EnableAnalytics=true`
- QuickSight account activated in your AWS account
- Admin access to QuickSight console
- IAM permissions to configure QuickSight service roles




### Step 1: Configure QuickSight Permissions

1. **Sign up for QuickSight** (if not already done):
   - Go to the [QuickSight console](https://quicksight.aws.amazon.com/)
   - Choose your region and complete the signup process
   - Select "Standard" or "Enterprise" edition based on your needs
   This will create the service linked roles for Quicksight.

2. **Configure QuickSight IAM Role**:
   - In QuickSight console, go to **Admin** → **Security & permissions**
   - Click **Manage QuickSight** → **Security & permissions**
   - Under **QuickSight access to AWS services**, click **Add or remove**
   - Enable the following services:
     - **Amazon Athena** ✅
     - **Amazon S3** ✅
   
3. **Configure S3 Access**:
   - In the S3 section, click **Select S3 buckets**
   - Find and select your buckets (replace `<unique-identifier>` with your actual value):
     - `s3-<unique-identifier>-caseprocessed` ✅
     - `s3-<unique-identifier>-athena-results` ✅
   - Click **Finish**

### Step 2: Create Athena Data Source

1. **Create New Data Source**:
   - In QuickSight, click **Datasets** → **New dataset**
   - Select **Athena** as the data source

2. **Configure Athena Connection**:
   - **Data source name**: `AWS Case Insights`
   - **Athena workgroup**: Use the workgroup name from your CloudFormation outputs (typically `CaseInsights-<unique-identifier>`)
   - Click **Create data source**

3. **Select Database and Table**:
   - **Database**: Select your database (typically `case_insights_<unique-identifier>`)
   - **Table**: Select `case_summary`
   - Choose **Import to SPICE** for better performance or **Directly query your data** for real-time results
   - Click **Select**

### Step 3: Create Analysis and Dashboard

1. **Prepare Data**:
   - Review the data fields and types
   - Create calculated fields if needed (e.g., date formatting)
   - Click **Save & visualize**

2. **Build Visualizations**:
   - Create charts for RCA categories, service codes, severity trends
   - Use filters for account numbers, date ranges, service codes
   - Add interactive elements like drill-downs

3. **Publish Dashboard**:
   - Click **Share** → **Publish dashboard**
   - Set permissions for other users in your organization
   - Configure refresh schedules if using SPICE


## Optional: Deploy MCP Server (Advanced)

If you want to enable AI platforms like Claude, ChatGPT, or other MCP-compatible tools to directly query and analyze your case insights data, you can optionally deploy the MCP (Model Context Protocol) server.  This option will deploy APIGW and a Lambda function that will act as a MCP server.  Authentication uses IAM credentials and there are backoffs and throttles to ensure subsystems are not overwhelmed. See Security.md for additional details.  See resources.md for what the stack creates.

### What is the MCP Server?

The MCP server provides a standardized API interface that allows AI tools to:
- Query your case insights data using natural language
- Perform automated analysis with Bedrock AI models
- Generate insights and trends from your support case data
- Integrate with platforms like Kiro, Claude Desktop, and other MCP clients

### Prerequisites for MCP Server

- **Case Insights deployed with analytics enabled** (`EnableAnalytics=true`)
- **Bedrock model access** (already configured in Step 1)
- **IAM permissions** for CloudFormation deployment

### Quick MCP Server Deployment

```bash
# Deploy the MCP server (replace with your values)
aws cloudformation create-stack \
  --stack-name mcp-case-insights \
  --template-body file://cloudformation/mcp-server-simple.yaml \
  --parameters \
    ParameterKey=UniqueIdentifier,ParameterValue=<your-unique-identifier> \
    ParameterKey=CaseInsightsStackName,ParameterValue=aws-case-insights \
    ParameterKey=BedrockModelId,ParameterValue=anthropic.claude-3-haiku-20240307-v1:0 \
  --capabilities CAPABILITY_NAMED_IAM
```

### Get Your MCP Endpoint

```bash
# Get the HTTPS endpoint URL
aws cloudformation describe-stacks \
  --stack-name mcp-case-insights \
  --query 'Stacks[0].Outputs[?OutputKey==`MCPServerEndpoint`].OutputValue' \
  --output text
```

### Grant User Access

```bash
# Get the user policy ARN and attach to your user
POLICY_ARN=$(aws cloudformation describe-stacks \
  --stack-name mcp-case-insights \
  --query 'Stacks[0].Outputs[?OutputKey==`MCPUserPolicyArn`].OutputValue' \
  --output text)

aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn $POLICY_ARN
```

### What You Get

The MCP server provides these capabilities:
- **Natural language queries**: "Show me critical cases from last month"
- **AI-powered analysis**: Automatic pattern detection and insights
- **Secure HTTPS API**: Built-in AWS authentication and encryption
- **Multiple tools**: Case summaries, RCA analysis, service trends, and more

### Complete Documentation

For detailed MCP server setup, configuration, security considerations, and integration with AI platforms, see the complete [MCP Server Deployment Guide](mcp-server-deployment.md).

The MCP server is optional but provides powerful AI integration capabilities for advanced users who want to enable conversational analysis of their case insights data.

## Testing

If you would like to test your new solution, you can wait until the nightly cycle (00:00 UTC) or you could create a test run which will start the processing.  Remember in a large organisation this is going to start a full run which could take hours to complete.

1. **Navigate to Lambda in the AWS Console**
2. **Find your function**: Search for `Lambda-AccountLookup-` followed by your unique ID
3. **Click on the function name** to open it
4. **Go to the "Test" tab**
5. **Create a new test event**:
   - **Event name**: `ScheduledEvent`
   - **Template**: Choose "Scheduled Event" or use custom JSON
   - **Event JSON**:
   ```json
   {
     "source": "aws.events",
     "detail-type": "Scheduled Event"
   }
   ```
6. **Click "Save"** to save the test event
7. **Click "Test"** to invoke the function

If you deployed the Athena stack the table will be empty, this is because the Crawler has not yet run.  Head over to Glue > Crawlers.  Click your crawler and click "run crawler".  Give it 5 minutes to run.