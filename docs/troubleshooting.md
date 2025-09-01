# Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using the Support Case Insights solution.

## Installation Issues

### CloudFormation Stack Creation Fails

**Symptoms:**
- CloudFormation stack creation fails with an error message
- Resources are not created or are partially created

**Possible Causes and Solutions:**

1. **Insufficient Permissions**
   - Ensure that the user or role deploying the CloudFormation template has the necessary permissions
   - Check the AWS CloudTrail logs for `AccessDenied` errors

2. **Resource Already Exists**
   - Check if resources with the same name already exist
   - Use a different `UniqueIdentifier` parameter value

3. **Service Limits**
   - Check if you've reached service limits for Lambda functions, SQS queues, or other resources
   - Request a service limit increase if necessary

4. **Invalid Template**
   - Validate the CloudFormation template using the AWS CLI:
     ```bash
     aws cloudformation validate-template --template-body file://cloudformation/case-insights.yaml
     ```

### Child Account Role Deployment Fails

**Symptoms:**
- CloudFormation stack creation for the child account role fails
- Cross-account access doesn't work

**Possible Causes and Solutions:**

1. **Incorrect Management Account ID**
   - Verify that the `ManagementAccountId` parameter is correct
   - Check the trust policy in the created role

2. **Organization ID Mismatch**
   - Ensure that the child account is part of the same AWS Organization
   - Check the `aws:PrincipalOrgID` condition in the trust policy

3. **Insufficient Permissions**
   - Ensure that the user or role deploying the template has the necessary permissions
   - Check the CloudTrail logs for `AccessDenied` errors

## Operational Issues

### Lambda Functions Fail

**Symptoms:**
- Lambda functions fail with error messages in CloudWatch Logs
- CloudWatch alarms for Lambda errors trigger

**Possible Causes and Solutions:**

1. **Insufficient Memory**
   - Check the memory usage in CloudWatch Metrics
   - Increase the memory allocation for the Lambda function

2. **Timeout**
   - Check the duration in CloudWatch Metrics
   - Increase the timeout for the Lambda function

3. **Permission Issues**
   - Check the CloudWatch Logs for `AccessDenied` errors
   - Verify that the Lambda execution role has the necessary permissions

4. **Code Errors**
   - Check the CloudWatch Logs for error messages
   - Fix the code and redeploy the Lambda function

### SQS Messages Not Processed

**Symptoms:**
- Messages accumulate in SQS queues
- CloudWatch alarms for queue depth trigger

**Possible Causes and Solutions:**

1. **Lambda Function Not Triggered**
   - Check the event source mapping for the Lambda function
   - Verify that the Lambda function has permission to receive messages from the queue

2. **Lambda Function Errors**
   - Check the CloudWatch Logs for error messages
   - Fix the code and redeploy the Lambda function

3. **Message Visibility Timeout**
   - Check if the visibility timeout is too short
   - Increase the visibility timeout for the queue

4. **Dead-Letter Queue**
   - Check if messages are being sent to the dead-letter queue
   - Investigate why messages are failing to process

### Step Functions Fail

**Symptoms:**
- Step Function executions fail
- CloudWatch alarms for Step Function failures trigger

**Possible Causes and Solutions:**

1. **Lambda Function Errors**
   - Check the CloudWatch Logs for error messages
   - Fix the code and redeploy the Lambda function

2. **Permission Issues**
   - Check the CloudWatch Logs for `AccessDenied` errors
   - Verify that the Step Function execution role has the necessary permissions

3. **Input/Output Format**
   - Check the input and output format for each step
   - Ensure that the output of one step matches the expected input of the next step

4. **Timeout**
   - Check if the Step Function execution times out
   - Increase the timeout for the Step Function or optimize the Lambda functions

### Bedrock API Issues

**Symptoms:**
- AI analysis fails
- CloudWatch Logs show Bedrock API errors

**Possible Causes and Solutions:**

1. **Throttling**
   - Check if the Bedrock API is throttling requests
   - Implement retry logic with backoff and jitter
   - Request a quota increase if necessary

2. **Model Not Available**
   - Verify that the specified model is available in your region
   - Use a different model if necessary

3. **Input Too Large**
   - Check if the input to the Bedrock API is too large
   - Truncate the input or split it into smaller chunks

4. **Permission Issues**
   - Verify that the Lambda function has permission to call the Bedrock API
   - Check the IAM policy for the Lambda execution role

## Data Issues

### Missing Cases

**Symptoms:**
- Cases are missing from the analysis
- Fewer cases than expected are processed

**Possible Causes and Solutions:**

1. **Cross-Account Access**
   - Verify that the `Support-Case-Analysis-Role` is correctly set up in each child account
   - Check the trust policy for the role

2. **Support API Permissions**
   - Ensure that the `Support-Case-Analysis-Role` has the `AWSSupportAccess` managed policy
   - Check the CloudWatch Logs for permission errors

3. **Case Age**
   - The solution only retrieves cases from the trailing 12 months
   - Modify the code to retrieve older cases if necessary

4. **Case Filtering**
   - Check if any filtering is applied in the code
   - Modify the code to include all cases if necessary

### Incorrect AI Analysis

**Symptoms:**
- AI analysis results are incorrect or unexpected
- RCA or lifecycle categories don't match expectations

**Possible Causes and Solutions:**

1. **Template Issues**
   - Check the templates used for AI analysis
   - Modify the templates to improve the results

2. **Model Selection**
   - Try a different Bedrock model
   - Adjust the model parameters (temperature, max tokens, etc.)

3. **Input Format**
   - Check the format of the input to the Bedrock API
   - Ensure that the case annotation is correctly formatted

4. **Output Parsing**
   - Check the parsing of the Bedrock API response
   - Ensure that the JSON response is correctly parsed

### Athena Query Issues

**Symptoms:**
- Athena queries fail or return unexpected results
- Data is not visible in Athena

**Possible Causes and Solutions:**

1. **Table Schema**
   - Verify that the table schema matches the data structure
   - Update the table schema if necessary

2. **Partitioning**
   - Run `MSCK REPAIR TABLE` to update the partitions
   - Check if the partitioning is correctly set up

3. **File Format**
   - Ensure that the data is stored in a format that Athena can read
   - Check if the SerDe is correctly configured

4. **Permissions**
   - Verify that the user or role has permission to query the data
   - Check the S3 bucket policy and IAM policies

## Monitoring Issues

### CloudWatch Alarms Not Triggering

**Symptoms:**
- CloudWatch alarms don't trigger when issues occur
- No notifications are received

**Possible Causes and Solutions:**

1. **Alarm Configuration**
   - Check the alarm configuration (threshold, evaluation period, etc.)
   - Verify that the alarm is in the `ALARM` state when issues occur

2. **SNS Subscription**
   - Ensure that the SNS topic has subscribers
   - Check if the subscription is confirmed

3. **Notification Delivery**
   - Check if the notification delivery is failing
   - Verify that the email address or endpoint is correct

4. **Metric Data**
   - Check if the metric data is being published
   - Verify that the metric namespace and name are correct

### CloudWatch Logs Not Available

**Symptoms:**
- CloudWatch Logs are not available or incomplete
- Log groups or log streams are missing

**Possible Causes and Solutions:**

1. **Logging Configuration**
   - Ensure that the Lambda functions are configured to log to CloudWatch
   - Check the log level in the code

2. **Permissions**
   - Verify that the Lambda execution role has permission to write to CloudWatch Logs
   - Check the IAM policy for the role

3. **Log Retention**
   - Check the log retention period
   - Configure log retention to keep logs for longer if necessary

4. **Log Volume**
   - Check if the log volume is too high
   - Reduce the log level or filter logs if necessary

## Performance Issues

### Slow Processing

**Symptoms:**
- Case processing takes longer than expected
- Step Function executions take a long time

**Possible Causes and Solutions:**

1. **Lambda Function Performance**
   - Check the duration of Lambda function executions
   - Optimize the code or increase the memory allocation

2. **API Throttling**
   - Check if the Support API or Bedrock API is throttling requests
   - Implement retry logic with backoff and jitter

3. **Concurrency Limits**
   - Check if Lambda concurrency limits are reached
   - Increase the concurrency limit if necessary

4. **Queue Depth**
   - Check the depth of SQS queues
   - Increase the number of consumers if necessary

### High Costs

**Symptoms:**
- AWS costs are higher than expected
- Specific services show high usage

**Possible Causes and Solutions:**

1. **Lambda Execution**
   - Check the number and duration of Lambda executions
   - Optimize the code to reduce execution time

2. **Bedrock API Usage**
   - Check the usage of the Bedrock API
   - Optimize the prompts or reduce the number of API calls

3. **S3 Storage**
   - Check the amount of data stored in S3
   - Implement lifecycle policies to delete or archive old data

4. **CloudWatch Logs**
   - Check the volume of CloudWatch Logs
   - Reduce the log level or implement log filtering

## Getting Help

If you're still experiencing issues after trying the solutions in this guide:

1. Check the CloudWatch Logs for detailed error messages
2. Review the [Architecture Overview](architecture.md) and [IAM Roles and Permissions](permissions.md) documents
3. Open an issue on the GitHub repository with:
   - A detailed description of the issue
   - Steps to reproduce the issue
   - Relevant error messages and logs
   - Your environment details (AWS region, account structure, etc.)