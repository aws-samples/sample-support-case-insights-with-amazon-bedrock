# Monitoring and Observability

This document provides detailed information about monitoring and observability for the Support Case Insights solution.

## Overview

The Support Case Insights solution includes comprehensive monitoring and observability features to ensure reliable operation and provide visibility into the system's performance. This document explains how to use these features to monitor the solution and troubleshoot issues.

## CloudWatch Metrics

The solution emits metrics to CloudWatch for all components. These metrics can be used to monitor the health and performance of the solution.

### Lambda Function Metrics

- **Invocations**: The number of times each Lambda function is invoked
- **Errors**: The number of errors that occur during Lambda function execution
- **Duration**: The time it takes for each Lambda function to execute
- **Throttles**: The number of times Lambda functions are throttled
- **ConcurrentExecutions**: The number of concurrent executions of Lambda functions
- **MemoryUsage**: The amount of memory used by Lambda functions

### SQS Queue Metrics

- **ApproximateNumberOfMessages**: The number of messages available for retrieval from the queue
- **ApproximateNumberOfMessagesDelayed**: The number of messages in the queue that are delayed
- **ApproximateNumberOfMessagesNotVisible**: The number of messages that are in flight
- **NumberOfMessagesSent**: The number of messages sent to the queue
- **NumberOfMessagesReceived**: The number of messages received from the queue
- **NumberOfMessagesDeleted**: The number of messages deleted from the queue
- **NumberOfEmptyReceives**: The number of ReceiveMessage API calls that did not return a message

### Step Function Metrics

- **ExecutionTime**: The time it takes for each Step Function execution to complete
- **ExecutionsStarted**: The number of Step Function executions started
- **ExecutionsSucceeded**: The number of Step Function executions that succeeded
- **ExecutionsFailed**: The number of Step Function executions that failed
- **ExecutionsTimedOut**: The number of Step Function executions that timed out

### S3 Bucket Metrics

- **BucketSizeBytes**: The amount of data stored in the S3 buckets
- **NumberOfObjects**: The number of objects stored in the S3 buckets

## CloudWatch Alarms

The solution creates CloudWatch alarms that notify you of potential issues. These alarms are configured to trigger when certain metrics exceed thresholds.

### Error Rate Alarms

- **LambdaErrorAlarm**: Triggers when Lambda functions have errors
- **StepFunctionFailureAlarm**: Triggers when Step Functions fail
- **DLQMessagesAlarm**: Triggers when messages are sent to dead-letter queues

### Performance Alarms

- **LambdaDurationAlarm**: Triggers when Lambda functions take too long to execute
- **StepFunctionExecutionTimeAlarm**: Triggers when Step Functions take too long to execute
- **SQSMessageAgeAlarm**: Triggers when messages in SQS queues are too old

### Throttling Alarms

- **LambdaThrottlingAlarm**: Triggers when Lambda functions are throttled
- **BedrockThrottlingAlarm**: Triggers when Bedrock API calls are throttled

## CloudWatch Dashboard

The solution creates a CloudWatch dashboard that provides visibility into the system's operation. The dashboard includes:

### System Overview

- Account processing status
- Case processing status
- Error rates
- Processing times

### Component Health

- Lambda function health
- SQS queue health
- Step Function health
- S3 bucket health

### Processing Metrics

- Number of accounts processed
- Number of cases processed
- Number of cases analyzed
- Processing time distribution

## Logging

The solution uses structured logging to provide detailed information about the system's operation.

### Log Groups

The solution creates the following CloudWatch Log Groups:

- `/aws/lambda/Lambda-AccountLookup-${UniqueIdentifier}`
- `/aws/lambda/Lambda-AccountReader-${UniqueIdentifier}`
- `/aws/lambda/Lambda-CaseRetrieval-${UniqueIdentifier}`
- `/aws/lambda/Lambda-CaseAnnotation-${UniqueIdentifier}`
- `/aws/lambda/Lambda-StartStepFunction-${UniqueIdentifier}`
- `/aws/lambda/Step-CaseSummary-${UniqueIdentifier}`
- `/aws/lambda/Step-RCAAnalysis-${UniqueIdentifier}`
- `/aws/lambda/Step-LifecycleAnalysis-${UniqueIdentifier}`
- `/aws/lambda/Step-UpdateCaseMetadata-${UniqueIdentifier}`

### Log Format

The logs use a structured format with the following fields:

- **timestamp**: The time the log entry was created
- **level**: The log level (INFO, WARNING, ERROR)
- **message**: The log message
- **function**: The function that generated the log
- **context**: Additional context information (account ID, case ID, etc.)

### Log Insights Queries

Here are some example CloudWatch Logs Insights queries for common troubleshooting scenarios:

#### Find Error Logs

```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

#### Track Case Processing

```
fields @timestamp, @message
| filter @message like /Processing case/
| sort @timestamp desc
| limit 100
```

#### Monitor Bedrock API Calls

```
fields @timestamp, @message
| filter @message like /Invoking Bedrock/
| sort @timestamp desc
| limit 100
```

#### Track Step Function Executions

```
fields @timestamp, @message
| filter @message like /Started Step Function execution/
| sort @timestamp desc
| limit 100
```

## X-Ray Tracing

The solution can be configured to use AWS X-Ray for distributed tracing. To enable X-Ray:

1. Add the `AWSXRayDaemonWriteAccess` managed policy to the Lambda execution roles
2. Set the `TracingConfig` property to `Active` for each Lambda function
3. Add the X-Ray SDK to the Lambda function code

With X-Ray enabled, you can:

- Visualize the request flow through the system
- Identify bottlenecks and latency issues
- Troubleshoot errors and failures

## Custom Metrics

You can add custom metrics to the solution by:

1. Using the CloudWatch PutMetricData API in the Lambda functions
2. Creating custom CloudWatch dashboards to visualize the metrics
3. Setting up CloudWatch alarms based on the custom metrics

Example custom metrics:

- **CasesProcessed**: The number of cases processed
- **AIAnalysisLatency**: The time it takes for AI analysis to complete
- **RCADistribution**: The distribution of RCA categories
- **LifecycleDistribution**: The distribution of lifecycle categories

## Best Practices

1. **Set Up Notifications**: Configure SNS notifications for CloudWatch alarms to receive alerts when issues occur
2. **Monitor Dead-Letter Queues**: Regularly check the dead-letter queues for messages that failed to process
3. **Review CloudWatch Logs**: Regularly review the CloudWatch Logs for error messages and warnings
4. **Adjust Alarm Thresholds**: Adjust the alarm thresholds based on your specific requirements and usage patterns
5. **Archive Logs**: Configure log retention and archiving to S3 for long-term storage and analysis
6. **Use Log Insights**: Use CloudWatch Logs Insights to analyze logs and identify patterns
7. **Monitor Costs**: Monitor the costs associated with the solution, especially Bedrock API usage