# MCP Server Deployment Guide

This guide explains how to deploy an MCP (Model Context Protocol) server that can interact with your Support Case Insights Athena tables and Bedrock for data analysis.

## HTTPS Certificate and Security

The MCP server provides secure HTTPS endpoints with zero certificate management required:

### Built-in HTTPS Security
- **AWS-Managed Certificates**: API Gateway automatically provides HTTPS with AWS-managed SSL/TLS certificates
- **TLS 1.3 Support**: Uses the latest TLS 1.3 protocol with strong cipher suites (AEAD-AES128-GCM-SHA256)
- **Certificate Validation**: SSL certificates are automatically validated and trusted by all major browsers and MCP clients
- **Zero Maintenance**: No certificate renewal, installation, or management required

### Endpoint Security Features
- **Endpoint Format**: `https://xxxxxxxxxx.execute-api.region.amazonaws.com/prod`
- **Regional Endpoints**: Certificates are region-specific and automatically provisioned

## ⚠️ **IMPORTANT: Network Security Considerations**

**The MCP server API Gateway endpoint is publicly accessible on the internet by default.** While it uses IAM authentication to secure access, the HTTPS endpoint itself can be reached from any IP address.

### **Current Security Model:**
- **IAM Authentication Required**: Only users with valid AWS credentials and the MCP user policy can access the API
- **HTTPS Encryption**: All communication is encrypted in transit
- **Public Internet Access**: The endpoint is reachable from anywhere (though authentication will block unauthorized users)

### **For Enhanced Network Security:**
If you need to restrict network access to internal networks only, consider these options:

1. **Private API Gateway**: Deploy the API Gateway as a private endpoint within your VPC
   - Requires VPC configuration and security groups
   - Only accessible from within your VPC or connected networks (VPN/Direct Connect)
   - Provides the highest level of network isolation

2. **VPC Endpoints**: Create VPC endpoints for API Gateway service
   - Route API calls through your private network infrastructure
   - Can be combined with security groups for additional access control

3. **API Gateway Resource Policy**: Add IP address restrictions to limit access to specific networks
   - Simpler to implement but requires managing static IP ranges
   - Still internet-exposed but restricted to allowed IPs

4. **Network Access Control**: Use your existing network security (firewalls, VPNs, etc.) to control access

**Note**: Implementing private networking requires additional VPC configuration, security groups, and networking expertise beyond the scope of this basic deployment guide. Consult your network security team for organization-specific requirements.

## Overview

The MCP server provides a standardized interface for AI tools to query your case insights data and perform analysis using Bedrock. This enables platforms like Claude, ChatGPT, or other AI systems to directly access and analyze your support case data.

## Architecture

The MCP server uses a **serverless architecture** built on AWS Lambda and API Gateway:

- **Serverless**: Pay-per-request, scales automatically, no infrastructure management
- **Authentication**: IAM authentication, HTTPS encryption, minimal permissions
- **Cost-effective**: Only pay when the API is used, no idle costs
- **Scalable**: Handles concurrent requests automatically
- **Integrated**: Direct access to your Case Insights Athena tables and Bedrock

## Prerequisites

1. **Existing Case Insights Deployment**: You must have already deployed the Case Insights solution with analytics enabled (`EnableAnalytics=true`). The standard stack name is `aws-case-insights` as shown in the [installation guide](installation.md).

2. **IAM Permissions for Deployment**: The user/role deploying the CloudFormation template needs the following permissions:

### Required CloudFormation Deployment Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudformation:GetTemplate"
      ],
      "Resource": "arn:aws:cloudformation:*:*:stack/mcp-case-insights-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:GetPolicy",
        "iam:ListPolicyVersions"
      ],
      "Resource": [
        "arn:aws:iam::*:role/MCPLambda-ExecutionRole-*",
        "arn:aws:iam::*:policy/MCPCaseInsights-UserAccess-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:DeleteFunction",
        "lambda:GetFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:GetPolicy"
      ],
      "Resource": "arn:aws:lambda:*:*:function:MCP-CaseInsights-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "apigateway:POST",
        "apigateway:DELETE",
        "apigateway:GET",
        "apigateway:PUT",
        "apigateway:PATCH"
      ],
      "Resource": "arn:aws:apigateway:*::/restapis*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:ListImports",
        "cloudformation:ListExports"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: If you're using an admin role or have broader permissions, these specific permissions may not be needed.

## Deployment Steps

1. **Deploy the MCP Server Stack**:
   ```bash
   aws cloudformation create-stack \
     --stack-name mcp-case-insights \
     --template-body file://cloudformation/mcp-server-simple.yaml \
     --parameters \
       ParameterKey=UniqueIdentifier,ParameterValue=your-unique-id \
       ParameterKey=CaseInsightsStackName,ParameterValue=aws-case-insights \
       ParameterKey=BedrockModelId,ParameterValue=anthropic.claude-3-haiku-20240307-v1:0 \
     --capabilities CAPABILITY_NAMED_IAM
   ```

   **Note**: The `CaseInsightsStackName` should be `aws-case-insights` (the standard stack name from the [installation guide](installation.md)). If you used a different stack name when deploying Case Insights, replace `aws-case-insights` with your actual stack name.

2. **Get the HTTPS Endpoint**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name mcp-case-insights \
     --query 'Stacks[0].Outputs[?OutputKey==`MCPServerEndpoint`].OutputValue' \
     --output text
   ```

3. **Grant User Access**:
   ```bash
   # Get the user policy ARN
   POLICY_ARN=$(aws cloudformation describe-stacks \
     --stack-name mcp-case-insights \
     --query 'Stacks[0].Outputs[?OutputKey==`MCPUserPolicyArn`].OutputValue' \
     --output text)
   
   # Attach to a user
   aws iam attach-user-policy \
     --user-name your-username \
     --policy-arn $POLICY_ARN
   ```
You can also grant access via a role and attaching the permission.

## AWS Resources Created

The CloudFormation template creates the following AWS resources:

### Core Compute Resources
- **AWS Lambda Function** (`MCP-CaseInsights-{UniqueIdentifier}`)
  - Runtime: Python 3.11
  - Memory: 1024 MB
  - Timeout: 5 minutes
  - Contains the MCP server logic and Bedrock integration

### API Gateway Resources
- **REST API** (`mcp-case-insights-api-{UniqueIdentifier}`)
  - Regional endpoint with built-in HTTPS
  - IAM authentication required
- **API Gateway Deployment** (prod stage)
- **API Gateway Resources** (proxy configuration for all paths)
- **API Gateway Methods** (ANY method with IAM auth)

### IAM Security Resources
- **Lambda Execution Role** (`MCPLambda-ExecutionRole-{UniqueIdentifier}`)
  - Permissions for Athena, Glue, S3, Bedrock, and CloudWatch Logs
  - Scoped to your specific Case Insights resources
- **User Access Policy** (`MCPCaseInsights-UserAccess-{UniqueIdentifier}`)
  - Allows users to invoke the API Gateway endpoints
  - Can be attached to users or roles

### Monitoring Resources
- **CloudWatch Log Group** (`/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}`)
  - Automatic logging of Lambda execution
  - 30-day retention period

### Resource Dependencies
The MCP server integrates with your existing Case Insights resources via CloudFormation imports:
- **S3 Buckets**: Reads from case processed data bucket and Athena results bucket
- **Athena Database**: Queries the `case_insights_{UniqueIdentifier}` database
- **Athena Workgroup**: Uses the `CaseInsights-{UniqueIdentifier}` workgroup

### Cost Breakdown
- **Lambda**: Pay per request (~$0.20 per 1M requests)
- **API Gateway**: Pay per request (~$3.50 per 1M requests)
- **CloudWatch Logs**: Pay per GB ingested (~$0.50 per GB)
- **Athena**: Pay per TB scanned (~$5 per TB)
- **Bedrock**: Pay per token (varies by model, ~$0.25 per 1K tokens for Claude Haiku)

**Typical monthly cost for moderate usage**: $5-20 per month

## Available MCP Tools

The MCP server provides the following tools:

### 1. `query_athena`
Execute custom Athena queries against your case insights data.

**Parameters**:
- `query` (string): SQL query to execute
- `max_results` (int, optional): Maximum number of results to return (default: 100)

**Example**:
```json
{
  "query": "SELECT COUNT(*) as total_cases, RCA_Category FROM case_summary GROUP BY RCA_Category",
  "max_results": 50
}
```

### 2. `analyze_with_bedrock`
Analyze data using Bedrock AI models.

**Parameters**:
- `data` (string): Data to analyze (JSON, CSV, or text format)
- `analysis_prompt` (string): Prompt describing the analysis you want

**Example**:
```json
{
  "data": "[{\"service\": \"EC2\", \"cases\": 45}, {\"service\": \"S3\", \"cases\": 23}]",
  "analysis_prompt": "Analyze these service case counts and identify trends"
}
```

### 3. `get_case_summary`
Get a summary of cases with optional filters.

**Parameters**:
- `account_number` (string, optional): Filter by specific AWS account
- `service_code` (string, optional): Filter by AWS service
- `days_back` (int, optional): Number of days to look back (default: 30)

**Example**:
```json
{
  "service_code": "EC2",
  "days_back": 60
}
```

### 4. `get_rca_analysis`
Get detailed RCA analysis for a specific category.

**Parameters**:
- `rca_category` (string): RCA category to analyze
- `limit` (int, optional): Maximum number of cases to return (default: 10)

**Example**:
```json
{
  "rca_category": "Throttling",
  "limit": 20
}
```

### 5. `get_service_trends`
Get service trends over time.

**Parameters**:
- `days_back` (int, optional): Number of days to analyze (default: 90)

**Example**:
```json
{
  "days_back": 180
}
```

### 6. `analyze_case_summaries`
Filter cases by multiple criteria and analyze their actual case summaries with Bedrock to identify top issues and patterns.

**Parameters**:
- `start_date` (string): Start date in YYYY-MM-DD format
- `end_date` (string): End date in YYYY-MM-DD format
- `severity_code` (string, optional): Filter by severity (low, normal, high, urgent, critical)
- `service_code` (string, optional): Filter by AWS service code (e.g., EC2, RDS, S3)
- `case_id` (string, optional): Filter by specific case ID
- `rca_category` (string, optional): Filter by RCA category
- `lifecycle_category` (string, optional): Filter by lifecycle category
- `analysis_question` (string, optional): Specific question to ask Bedrock
- `max_cases` (int, optional): Maximum number of cases to analyze (default: 200)

**Examples**:

**Analyze critical cases:**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "severity_code": "critical",
  "analysis_question": "What are the top problems you're seeing in critical cases?"
}
```

**Analyze EC2 issues:**
```json
{
  "start_date": "2024-12-01",
  "end_date": "2024-12-31",
  "service_code": "EC2",
  "analysis_question": "What are the most common EC2 issues and their patterns?"
}
```

**Analyze throttling issues:**
```json
{
  "start_date": "2024-11-01",
  "end_date": "2024-11-30",
  "rca_category": "Throttling",
  "analysis_question": "What services are experiencing throttling and why?"
}
```

**Multi-filter analysis:**
```json
{
  "start_date": "2024-12-15",
  "end_date": "2024-12-31",
  "severity_code": "high",
  "service_code": "RDS",
  "analysis_question": "What high-severity RDS issues occurred during the holiday period?"
}
```

### **Response Format:**

The `analyze_case_summaries` tool returns a comprehensive analysis with the following structure:

```json
{
  "filters_applied": {
    "date_range": "2025-01-01 to 2025-03-01",
    "severity_code": "critical",
    "service_code": null,
    "case_id": null,
    "rca_category": null,
    "lifecycle_category": null
  },
  "total_cases_found": 45,
  "summaries_available": 42,
  "summaries_analyzed": 42,
  "token_management": {
    "estimated_input_tokens": 28500,
    "max_input_tokens": 180000,
    "truncated": false
  },
  "analysis_question": "If you filter by critical cases, what are the top problems that you are seeing?",
  "analysis": "**TOP ISSUES IDENTIFIED:**\n1. Database connection timeouts (15 cases)\n2. Auto Scaling failures during peak load (12 cases)\n3. Network connectivity issues (8 cases)\n...\n\n**PATTERNS & TRENDS:**\n- Most critical issues occur during business hours (9 AM - 5 PM)\n- EC2 and RDS account for 70% of critical cases\n...",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "sample_cases": [
    {
      "case_number": "12345678901",
      "service": "EC2", 
      "severity": "critical",
      "rca_category": "Performance",
      "date": "2025-01-15"
    }
  ],
  "query_execution_id": "12345-abcd-..."
}
```

## MCP Protocol Support

The server supports both **REST API** and **MCP Protocol** interfaces:

### MCP Protocol Endpoints
- **Protocol**: JSON-RPC 2.0 over HTTPS
- **Endpoint**: `https://your-endpoint/mcp`
- **Methods**: `tools/list`, `tools/call`

### REST API Endpoints (Backward Compatibility)
- **Protocol**: Standard REST over HTTPS
- **Endpoints**: `https://your-endpoint/tools/*`
- **Methods**: GET, POST

## Why a Client Wrapper is Required

**Important**: The MCP server runs on AWS API Gateway, which uses **HTTP REST endpoints**. However, MCP clients (like Kiro) expect tools to communicate via **stdin/stdout using JSON-RPC protocol**.

### Protocol Translation Challenge
```
MCP Client (Kiro) ↔ stdin/stdout JSON-RPC ↔ [WRAPPER NEEDED] ↔ HTTP REST ↔ AWS API Gateway
```

The `mcp_aws_client.py` wrapper bridges this gap by:
- **Protocol Translation**: Converting stdin/stdout ↔ HTTP REST requests
- **AWS Authentication**: Handling AWS SigV4 authentication automatically  
- **Format Conversion**: Translating MCP JSON-RPC to API Gateway format
- **Credential Management**: Supporting multiple AWS credential sources

Without this wrapper, MCP clients cannot communicate with the AWS-hosted MCP server.

## MCP Client Wrapper Setup

### Download the Client Wrapper

Create the required client wrapper file in your project directory:

**Copy the code directly**

Save the following code as `mcp_aws_client.py` in your project directory:

```python
#!/usr/bin/env python3
"""
AWS Case Insights MCP Server
Implements proper MCP protocol with AWS SigV4 authentication
"""

import json
import sys
import os
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import InstanceMetadataProvider, EnvProvider, SharedCredentialProvider, ContainerProvider
from botocore.session import get_session

# MCP Protocol constants
MCP_VERSION = "2024-11-05"

class MCPServer:
    def __init__(self, mcp_url, aws_region):
        self.mcp_url = mcp_url
        self.aws_region = aws_region
        self.credentials = None
        self.initialized = False
        
    def setup_credentials(self):
        """Set up AWS credentials from various sources"""
        credential_source = "unknown"
        
        # Method 1: Try environment variables first
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
            session = boto3.Session(
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
                region_name=self.aws_region
            )
            self.credentials = session.get_credentials()
            credential_source = "environment variables"
        
        # Method 2: Try AWS CLI profile/config files
        if not self.credentials:
            try:
                session = boto3.Session(region_name=self.aws_region)
                self.credentials = session.get_credentials()
                if self.credentials:
                    credential_source = "AWS CLI profile/config"
            except Exception:
                pass
        
        # Method 3: Try instance metadata (for EC2/ECS)
        if not self.credentials:
            try:
                botocore_session = get_session()
                instance_provider = InstanceMetadataProvider(botocore_session)
                self.credentials = instance_provider.load()
                if self.credentials:
                    credential_source = "instance metadata"
            except Exception:
                pass
        
        # Method 4: Try container credentials (for ECS tasks)
        if not self.credentials:
            try:
                botocore_session = get_session()
                container_provider = ContainerProvider(botocore_session)
                self.credentials = container_provider.load()
                if self.credentials:
                    credential_source = "container credentials"
            except Exception:
                pass
        
        if not self.credentials:
            raise Exception("AWS credentials not found. Please configure AWS CLI or set environment variables.")
        
        print(f"Using AWS credentials from: {credential_source}", file=sys.stderr)
        
    def handle_initialize(self, request_id, params):
        """Handle MCP initialize request"""
        self.initialized = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": MCP_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "aws-case-insights",
                    "version": "1.0.0"
                }
            }
        }
    
    def handle_tools_list(self, request_id):
        """Handle tools/list request by forwarding to HTTP MCP server"""
        try:
            # Forward request to HTTP MCP server
            data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list",
                "params": {}
            }
            
            request = AWSRequest(
                method='POST',
                url=f"{self.mcp_url}/mcp",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'}
            )
            
            SigV4Auth(self.credentials, 'execute-api', self.aws_region).add_auth(request)
            
            response = requests.post(
                request.url,
                data=request.body,
                headers=dict(request.headers),
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def handle_tools_call(self, request_id, params):
        """Handle tools/call request by forwarding to HTTP MCP server"""
        try:
            # Forward request to HTTP MCP server
            data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": params
            }
            
            request = AWSRequest(
                method='POST',
                url=f"{self.mcp_url}/mcp",
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'}
            )
            
            SigV4Auth(self.credentials, 'execute-api', self.aws_region).add_auth(request)
            
            response = requests.post(
                request.url,
                data=request.body,
                headers=dict(request.headers),
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def handle_request(self, request_data):
        """Handle incoming MCP request"""
        try:
            method = request_data.get('method')
            request_id = request_data.get('id')
            params = request_data.get('params', {})
            
            if method == 'initialize':
                return self.handle_initialize(request_id, params)
            elif method == 'tools/list':
                if not self.initialized:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32002,
                            "message": "Server not initialized"
                        }
                    }
                return self.handle_tools_list(request_id)
            elif method == 'tools/call':
                if not self.initialized:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32002,
                            "message": "Server not initialized"
                        }
                    }
                return self.handle_tools_call(request_id, params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_data.get('id'),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

def main():
    # Get MCP server URL from environment
    mcp_url = os.environ.get('MCP_SERVER_URL')
    if not mcp_url:
        print(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32000,
                "message": "MCP_SERVER_URL environment variable not set"
            }
        }))
        sys.exit(1)
    
    # Get AWS region
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Create MCP server instance
    server = MCPServer(mcp_url, aws_region)
    
    try:
        # Set up AWS credentials
        server.setup_credentials()
        
        # Read MCP requests from stdin and process them
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse MCP request
                    request_data = json.loads(line)
                    
                    # Handle the request
                    response = server.handle_request(request_data)
                    
                    # Send response
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                except Exception as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response))
                    sys.stdout.flush()
                
        except EOFError:
            # End of input, exit gracefully
            pass
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            pass
                
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32000,
                "message": f"Failed to initialize: {str(e)}"
            }
        }
        print(json.dumps(error_response))
        sys.exit(1)

if __name__ == "__main__":
    main()
```


### Install Required Dependencies

The client wrapper requires these Python packages:

```bash
pip install boto3 requests botocore
```

### Make the Script Executable

```bash
chmod +x mcp_aws_client.py
```

## Testing the MCP Server

### Authentication Requirements

⚠️ **Important**: All API calls require AWS IAM authentication. Regular `curl` commands will fail with "missing authentication token" errors.

**Solutions for testing:**

1. **Install awscurl** (Recommended):
   ```bash
   pip install awscurl
   ```

2. **Use AWS CLI with signed requests**:
   ```bash
   # Create a temporary file with your request body
   echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' > request.json
   
   # Use aws-cli to make signed request
   aws --region us-east-1 apigateway invoke-rest-api \
     --rest-api-id $(echo $ENDPOINT | cut -d'/' -f3 | cut -d'.' -f1) \
     --resource-path "/mcp" \
     --http-method POST \
     --body fileb://request.json \
     response.json && cat response.json
   ```

3. **Use Postman** with AWS Signature v4 authentication

4. **Use a Python script** with boto3:
   ```python
   import boto3
   import json
   import requests
   from botocore.auth import SigV4Auth
   from botocore.awsrequest import AWSRequest
   
   # Your endpoint URL
   endpoint = "https://your-api-gateway-url.execute-api.region.amazonaws.com/prod"
   
   # Create AWS session
   session = boto3.Session()
   credentials = session.get_credentials()
   
   # Prepare request
   url = f"{endpoint}/mcp"
   data = {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list",
       "params": {}
   }
   
   # Sign and send request
   request = AWSRequest(method='POST', url=url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
   SigV4Auth(credentials, 'execute-api', session.region_name).add_auth(request)
   response = requests.post(url, data=request.body, headers=dict(request.headers))
   print(response.json())
   ```

5. **Use your MCP client** (like Kiro) which handles authentication automatically

### Test Basic Connectivity
```bash
# Get the endpoint from CloudFormation outputs
ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name mcp-case-insights \
  --query 'Stacks[0].Outputs[?OutputKey==`MCPServerEndpoint`].OutputValue' \
  --output text)

# Test basic connectivity using awscurl
awscurl $ENDPOINT/ --service execute-api
```

### Test MCP Protocol
```bash
# Test MCP tools list
# Using awscurl (Recommended - handles AWS authentication automatically)
# Install awscurl: pip install awscurl
awscurl -X POST $ENDPOINT/mcp \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Test MCP tool call (using awscurl for authentication)
awscurl -X POST $ENDPOINT/mcp \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_case_summary",
      "arguments": {"days_back": 30}
    }
  }'

# Test the new case summary analysis tool (using awscurl)
awscurl -X POST $ENDPOINT/mcp \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "analyze_case_summaries",
      "arguments": {
        "start_date": "2025-01-01",
        "end_date": "2025-07-30",
        "severity_code": "critical",
        "analysis_question": "What are the top problems in critical cases?"
      }
    }
  }'
```

### Test Tool Listing
```bash
# Using awscurl (install with: pip install awscurl)
awscurl $ENDPOINT/tools --service execute-api
```

### Test a Query Tool
```bash
# Using awscurl for authentication
awscurl -X POST $ENDPOINT/tools/get_case_summary \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{"days_back": 30}'
```

### Test Athena Query
```bash
# Test with a simple query first to verify connectivity
awscurl -X POST $ENDPOINT/tools/query_athena \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SHOW TABLES",
    "max_results": 10
  }'

# Test with a basic count query (adjust table name as needed)
awscurl -X POST $ENDPOINT/tools/query_athena \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT COUNT(*) as total_cases FROM case_summary LIMIT 10",
    "max_results": 10
  }'

# Test with date filtering (using proper Athena syntax)
awscurl -X POST $ENDPOINT/tools/query_athena \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT COUNT(*) as total_cases FROM case_summary WHERE from_iso8601_timestamp(timecreated) >= current_date - interval '\''30'\'' day",
    "max_results": 10
  }'
```

### Test Case Summary Analysis with Bedrock
```bash
# Analyze critical cases for a specific period (using awscurl)
awscurl -X POST $ENDPOINT/tools/analyze_case_summaries \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-07-30",
    "severity_code": "critical",
    "analysis_question": "If you filter by critical cases, what are the top problems that you are seeing?"
  }'

# Analyze EC2 issues with high severity (using awscurl)
awscurl -X POST $ENDPOINT/tools/analyze_case_summaries \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-07-30",
    "service_code": "EC2",
    "severity_code": "high",
    "analysis_question": "What are the most common high-severity EC2 problems and their root causes?"
  }'

# Analyze throttling issues across all services (using awscurl)
awscurl -X POST $ENDPOINT/tools/analyze_case_summaries \
  --service execute-api \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-07-30",
    "rca_category": "Service Event",
    "analysis_question": "What services are experiencing throttling issues and what patterns do you see?"
  }'
```

## Integration with AI Platforms

### Using with Kiro MCP

1. **Get Your MCP Server URL**:
   
   First, retrieve your API Gateway endpoint URL from the CloudFormation stack:
   
   ```bash
   # Get the MCP server endpoint URL
   ENDPOINT=$(aws cloudformation describe-stacks \
     --stack-name mcp-case-insights \
     --query 'Stacks[0].Outputs[?OutputKey==`MCPServerEndpoint`].OutputValue' \
     --output text)
   
   echo "Your MCP Server URL: $ENDPOINT"
   ```
   
   **Alternative using AWS CLI (QCLI)**:
   ```bash
   # Using describe-stacks with different output format
   aws cloudformation describe-stacks \
     --stack-name mcp-case-insights \
     --output table \
     --query 'Stacks[0].Outputs[?OutputKey==`MCPServerEndpoint`]'
   
   # Or get all outputs to see available endpoints
   aws cloudformation describe-stacks \
     --stack-name mcp-case-insights \
     --query 'Stacks[0].Outputs' \
     --output table
   ```

2. **Setup the Client Wrapper**:
   
   First, ensure you have the `mcp_aws_client.py` file in your project directory wihch you created earlier (see the "MCP Client Wrapper Setup" section above).

3. **Configure MCP in Kiro**:
   
   Create or update `.kiro/settings/mcp.json` in your project workspace with your actual endpoint URL:

   ```json
    {
      "mcpServers": {
        "aws-case-insights": {
          "command": "/<path to kiro environment>/.kiro/start_mcp_server.sh",
          "args": [],
          "env": {
            "MCP_SERVER_URL": "<Your URL Endpoint from APIGW>",
            "AWS_REGION": "us-east-1"
          },
          "disabled": false,
          "autoApprove": [
            "get_case_summary",
            "get_service_trends",
            "get_rca_analysis",
            "query_athena",
            "analyze_with_bedrock",
            "analyze_case_summaries"
          ]
        }
      }
    }
  ```
  
  Create a wrapper script for starting the MCP and save as start_mcp_server.sh within your workspace:

  ```bash
  #!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set environment variables
export MCP_SERVER_URL="${MCP_SERVER_URL:-https://<APIGW URL>/v1}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

# Execute the Python MCP server
exec "$SCRIPT_DIR/mcp_venv/bin/python" "$SCRIPT_DIR/mcp_aws_client.py" "$@"
```
NOTE:  Remember to replace the APIGW URL with your URL.

Restart Kiro, you will get an error that the MCP server could not start, this is credential related. 

Before moving onto testing, make sure that credentials have been added to environmental variables and then to the aws credentials file by running:

```bash
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
aws_session_token = $AWS_SESSION_TOKEN
EOF
```

You should now be able to click the reconnect button on the MCP Servers section of Kiro on the left pannel (the little ghost).  The reconnect button will show when you hover over the MCP server.

You should see "Connected" which means you're good to test using conversation in the Kiro describe task window.  

4. **Test the Integration**:
   
   After configuring Kiro, restart Kiro or reconnect the MCP server from the MCP Server view in the Kiro feature panel.
   
   **Test commands in Kiro chat**:
   - "Show me a summary of cases from the last 30 days"
   - "Analyze EC2 service trends over the last 90 days"
   - "Get RCA analysis for throttling issues"
   - "What are the top problems in critical cases from January 2025?"
   - "Analyze high-severity RDS issues from last month"
   
   **Verify MCP tools are available**:
   In Kiro, you can check if the MCP tools are loaded by asking:
   - "What MCP tools are available for case insights?"
   - "List the available case analysis tools"
   
   **Troubleshooting Kiro Integration**:
   - **MCP server not connecting**: Check that `mcp_aws_client.py` exists and Python dependencies are installed (`pip install boto3 requests botocore`)
   - **Authentication errors**: Ensure your AWS credentials are configured (`aws configure`)
   - **Tool not found errors**: Verify the MCP server URL is correct and accessible
   - **Permission errors**: Confirm you have the MCP user policy attached to your AWS user/role
   - **Python path issues**: Use absolute path to `mcp_aws_client.py` if needed
   - **Environment variables**: Verify `MCP_SERVER_URL` and `AWS_REGION` are set correctly

### Using with Other AI Platforms

The MCP server exposes a REST API that can be integrated with any AI platform that supports HTTP requests. The API follows standard REST conventions:

- `GET /` - Server information
- `GET /tools` - List available tools
- `POST /tools/{tool_name}` - Execute a specific tool

## Security Considerations

⚠️ **IMPORTANT**: The MCP server provides access to sensitive AWS support case data. Proper authentication is critical.

### Authentication & Authorization

**IAM Authentication**:
- API Gateway requires AWS IAM credentials for all requests
- Users need the `MCPCaseInsights-UserAccess-{UniqueIdentifier}` policy attached
- Requests must be signed with AWS Signature Version 4
- Integrates with existing AWS identity management

**Setting up user access**:
```bash
# Attach the policy to a user
aws iam attach-user-policy \
  --user-name your-mcp-user \
  --policy-arn arn:aws:iam::123456789012:policy/MCPCaseInsights-UserAccess-your-unique-id

# Or attach to a role for cross-account access
aws iam attach-role-policy \
  --role-name your-mcp-role \
  --policy-arn arn:aws:iam::123456789012:policy/MCPCaseInsights-UserAccess-your-unique-id
```

**Making authenticated requests**:
```bash
# Using AWS CLI with credentials
aws apigatewayv2 invoke \
  --api-id your-api-id \
  --stage prod \
  --route-key "POST /tools/analyze_case_summaries" \
  --body '{"start_date":"2025-01-01","end_date":"2025-01-31"}'

# Using curl with AWS signature (requires aws-cli or SDK)
curl -X POST https://your-api-gateway-url/prod/tools/analyze_case_summaries \
  --aws-sigv4 "aws:amz:us-east-1:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2025-01-01","end_date":"2025-01-31"}'
```


### Network Security
- **HTTPS only**: All communication encrypted in transit
- **Private deployment**: Consider VPC endpoints for internal-only access
- **WAF integration**: Add AWS WAF for additional protection against attacks
- **Rate limiting**: Built-in API Gateway throttling protects against abuse

### IAM Security (Implemented)
- **Principle of least privilege**: MCP server has minimal required permissions
- **Resource-scoped permissions**: Limited to your specific Case Insights resources
- **IAM authentication**: API Gateway requires valid AWS credentials
- **User access policy**: Managed policy controls who can access the API

### Data Security (Implemented)
- **Data residency**: All data remains within your AWS account and region
- **Encryption**: Data encrypted at rest (S3, Athena) and in transit (HTTPS)
- **No data persistence**: MCP server doesn't store or cache case data
- **CloudWatch logging**: Lambda execution logs for troubleshooting

## Logging and Monitoring

The MCP server provides comprehensive logging for security monitoring, debugging, and performance analysis.

### API Gateway Access Logs

**Log Group**: `/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}`

**Purpose**: Complete audit trail of all API requests

**What's Logged**:
- Request timestamp and unique ID
- Client IP address and user agent
- HTTP method and resource path
- Response status and timing
- IAM user/role information
- Request and response sizes

**Example Log Entry**:
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

### Lambda Function Logs

**Log Group**: `/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}`

**Purpose**: Application-level logging for MCP operations

**What's Logged**:
- Tool execution details
- Athena query performance
- Bedrock analysis results
- Error messages and stack traces

**Example Log Entries**:
```
[INFO] Executing tool: analyze_case_summaries
[INFO] Athena query started: 12345-67890-abcdef
[INFO] Query returned 150 cases for analysis
[INFO] Bedrock analysis completed: 2.3 seconds
[ERROR] Athena query failed: InvalidQueryException
```

### Monitoring Best Practices

**Security Monitoring**:
```bash
# Monitor authentication failures
aws logs filter-log-events \
  --log-group-name "/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}" \
  --filter-pattern "{ $.status = 403 }"

# Monitor throttling events
aws logs filter-log-events \
  --log-group-name "/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}" \
  --filter-pattern "{ $.status = 429 }"
```

**Performance Monitoring**:
```bash
# Monitor slow requests (>5 seconds)
aws logs filter-log-events \
  --log-group-name "/aws/apigateway/mcp-case-insights-access-{UniqueIdentifier}" \
  --filter-pattern "{ $.responseTime > 5000 }"

# Monitor application errors
aws logs filter-log-events \
  --log-group-name "/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}" \
  --filter-pattern "ERROR"
```

**Usage Analytics**:
- Track API usage patterns by user
- Monitor popular tools and queries
- Analyze response times and performance trends
- Identify heavy users for capacity planning

### Log Retention

**Default Settings**:
- **API Gateway Access Logs**: 30 days retention
- **Lambda Function Logs**: Indefinite (AWS default)

**Cost Optimization**:
Consider setting retention policies for Lambda logs:
```bash
aws logs put-retention-policy \
  --log-group-name "/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}" \
  --retention-in-days 30
```

For detailed logging information across the entire Case Insights solution, see the [Logging Guide](logging.md).

### Optional Security Enhancements (Not Implemented)
- **CloudTrail**: Enable in your account to log all API Gateway calls for audit purposes
- **AWS WAF**: Add web application firewall for additional protection
- **VPC Endpoints**: Deploy API Gateway privately within your VPC
- **API Gateway access logging**: Enable detailed request/response logging
- **Cross-account access**: Use IAM roles for secure cross-account scenarios

## Monitoring and Troubleshooting

### CloudWatch Logs
- Lambda execution logs: Check `/aws/lambda/MCP-CaseInsights-{UniqueIdentifier}` log group

### Common Issues

1. **Athena query failures**:
   - **"Table not found"**: Check your table name with `SHOW TABLES` query
   - **"Database not found"**: Verify the database name matches your UniqueIdentifier
   - **"Syntax error"**: Use Athena v3 compatible syntax (see examples above)
   - **"Access denied"**: Ensure Lambda has proper Glue/Athena permissions
   
   **Debug steps**:
   ```bash
   # 1. Check what databases exist
   awscurl -X POST $ENDPOINT/tools/query_athena \
     --service execute-api \
     -H "Content-Type: application/json" \
     -d '{"query": "SHOW DATABASES"}'
   
   # 2. Check what tables exist in your database
   awscurl -X POST $ENDPOINT/tools/query_athena \
     --service execute-api \
     -H "Content-Type: application/json" \
     -d '{"query": "SHOW TABLES"}'
   
   # 3. Check table schema
   awscurl -X POST $ENDPOINT/tools/query_athena \
     --service execute-api \
     -H "Content-Type: application/json" \
     -d '{"query": "DESCRIBE case_summary"}'
   ```

2. **"No export named" errors during deployment**:
   - **Most common cause**: Wrong Case Insights stack name
   - **Standard stack name**: `aws-case-insights` (from installation guide)
   - **Check your actual stack name**:
     ```bash
     aws cloudformation list-stacks \
       --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
       --query 'StackSummaries[?contains(StackName, `case`) || contains(StackName, `insights`)].StackName' \
       --output table
     ```
   - **Verify exports exist**:
     ```bash
     aws cloudformation list-exports \
       --query 'Exports[?contains(Name, `your-unique-id`)].Name' \
       --output table
     ```

2. **"Table not found" errors**:
   - Ensure your Case Insights stack has `EnableAnalytics=true`
   - Run `MSCK REPAIR TABLE` to discover partitions
   - Verify the database name matches your UniqueIdentifier

3. **Permission denied errors**:
   - Check IAM role permissions
   - Verify the Case Insights stack name is correct
   - Ensure cross-stack references are working

3. **Bedrock access errors**:
   - Verify Bedrock model access in your region
   - Check if the model ID is correct and available
   - Ensure Bedrock service is enabled in your account

### Performance Optimization

1. **Query Optimization**:
   - Use partition pruning in Athena queries
   - Limit result sets with appropriate WHERE clauses
   - Consider creating views for common queries

2. **Cost Optimization**:
   - Use the Lambda version for occasional use
   - Set appropriate timeout values
   - Monitor Athena query costs and optimize expensive queries

## Data Access Control & Scoping

The solution currently shows you all case data which limits the scope of who should have access.  It's possible to implement fine-grained access control to restrict what data users can see through the MCP interface. If you're considering giving application teams direct access to analyse their own cases you might want to consider the following modifications.  Consider:

### Athena Views with Row-Level Security

Create Athena views that filter data based on user context:

```sql
-- Create a view that filters by business unit based on role
CREATE VIEW case_summary_filtered AS
SELECT *
FROM case_summary
WHERE business_unit IN (
     SELECT allowed_bu 
     FROM role_business_unit_mapping 
     WHERE role_name = '${aws:requested-role}'
   )
   OR '${aws:requested-role}' LIKE '%admin%'  -- Admin roles see all data
   OR '${aws:requested-role}' LIKE '%global%'; -- Global roles see all data
```
Create a role, add Business Unit into the case data (you could modify the Lambda to pull this from a list)
**Implementation steps:**
1. Add business unit data to your case ingestion process
2. Create role-to-business-unit mapping table
3. Create filtered views in Athena
4. Update MCP server to use views instead of base tables

When you give out the credentials to the users, this would limit the data that is brought back for the customer. 

## Extending the MCP Server

You can extend the MCP server by:

1. **Adding New Tools**: Modify the Lambda function or container code to add new analysis functions
2. **Custom Queries**: Create predefined queries for common analysis patterns
3. **Data Enrichment**: Add external data sources or APIs for enhanced analysis
4. **Caching**: Implement caching for frequently accessed data
5. **Access Control**: Implement the data scoping approaches described above

## Cost Estimation

### Lambda Version
- API Gateway: ~$3.50 per million requests
- Lambda: ~$0.20 per million requests (100ms average)
- Athena: ~$5 per TB scanned
- Bedrock: Varies by model (~$0.25 per 1K input tokens for Claude Haiku)

# **Token Management & Performance**

The `analyze_case_summaries` tool includes intelligent token management to prevent hitting Claude's limits:

### **Token Limits:**
- **Claude 3 Haiku**: 200K input tokens, 4K output tokens
- **Safe limit**: 180K input tokens (leaves buffer for prompt)
- **Optimized summaries**: Target 650 characters (~163 tokens)
- **Truncation limit**: 700 characters (~175 tokens)

### **Smart Processing:**
- **Optimized template** targets 650 characters per summary
- **Truncation limit** of 700 characters (rarely needed)
- **Estimates tokens** for each case summary (~175 tokens each)
- **Prioritizes by severity** (critical cases first, then by date)
- **Stops before hitting limits** and reports truncation
- **Typical capacity**: ~1,000 case summaries in one call

## IAM Permissions Reference

This section details the IAM permissions specific to the MCP server CloudFormation template. For comprehensive information about all IAM roles and permissions used by the Support Case Insights solution, see the [Permissions Guide](permissions.md).

**Important**: The MCP server creates its own separate IAM roles and policies that are independent of the main Case Insights solution roles. The MCP server accesses the same data through Athena queries but uses different execution roles with appropriate permissions.

### Relationship to Main Case Insights Permissions

| Component | Main Solution Role | MCP Server Role | Purpose |
|-----------|-------------------|-----------------|---------|
| Lambda Execution | `CaseInsights-LambdaExecutionRole-${UniqueIdentifier}` | `MCPLambda-ExecutionRole-{UniqueIdentifier}` | Different Lambda functions, same data access |
| Bedrock Access | `CaseInsights-BedrockExecutionRole-${UniqueIdentifier}` | Included in MCP Lambda role | Both need Bedrock for AI analysis |
| User Access | N/A (direct Lambda invocation) | `MCPCaseInsights-UserAccess-{UniqueIdentifier}` | MCP needs API Gateway access control |
| Data Access | S3 + Step Functions | S3 + Athena + Glue | Different access patterns for same data |

Both solutions access the same underlying data but through different mechanisms:
- **Main Solution**: Processes cases via Lambda → S3 → Step Functions
- **MCP Server**: Queries processed data via API Gateway → Lambda → Athena

### MCP Lambda Execution Role: `MCPLambda-ExecutionRole-{UniqueIdentifier}`

The MCP Lambda function runs with these permissions (separate from the main Case Insights roles documented in [permissions.md](permissions.md)):

#### Basic Lambda Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream", 
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

#### Athena Query Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "athena:BatchGetQueryExecution",
    "athena:GetQueryExecution",
    "athena:GetQueryResults", 
    "athena:StartQueryExecution",
    "athena:StopQueryExecution",
    "athena:GetWorkGroup",
    "athena:ListQueryExecutions"
  ],
  "Resource": [
    "arn:aws:athena:*:*:workgroup/CaseInsights-{UniqueIdentifier}",
    "arn:aws:athena:*:*:workgroup/primary"
  ]
}
```

#### Glue Catalog Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "glue:GetDatabase",
    "glue:GetTable", 
    "glue:GetPartitions",
    "glue:GetTables"
  ],
  "Resource": [
    "arn:aws:glue:*:*:catalog",
    "arn:aws:glue:*:*:database/case_insights_{UniqueIdentifier}",
    "arn:aws:glue:*:*:table/case_insights_{UniqueIdentifier}/*"
  ]
}
```

#### S3 Data Access Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::s3-{UniqueIdentifier}-caseprocessed",
    "arn:aws:s3:::s3-{UniqueIdentifier}-caseprocessed/*"
  ]
},
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:ListBucket",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:GetBucketLocation"
  ],
  "Resource": [
    "arn:aws:s3:::s3-{UniqueIdentifier}-athena-results", 
    "arn:aws:s3:::s3-{UniqueIdentifier}-athena-results/*"
  ]
}
```

#### Bedrock AI Model Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:ListFoundationModels"
  ],
  "Resource": "arn:aws:bedrock:*::foundation-model/*"
}
```

### MCP User Access Policy: `MCPCaseInsights-UserAccess-{UniqueIdentifier}`

Users/roles need this policy to access the MCP API (this is additional to the main Case Insights permissions):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "execute-api:Invoke"
      ],
      "Resource": "arn:aws:execute-api:{Region}:{AccountId}:{ApiGatewayId}/*/*"
    }
  ]
}
```

### Cross-Account Access

To grant access to users in other AWS accounts:

1. **Create a role in the target account**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::TARGET-ACCOUNT:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

2. **Attach the MCP user policy to the role**:
```bash
aws iam attach-role-policy \
  --role-name CrossAccountMCPAccess \
  --policy-arn arn:aws:iam::SOURCE-ACCOUNT:policy/MCPCaseInsights-UserAccess-{UniqueIdentifier}
```

3. **Users in the target account assume the role**:
```bash
aws sts assume-role \
  --role-arn arn:aws:iam::SOURCE-ACCOUNT:role/CrossAccountMCPAccess \
  --role-session-name mcp-access
```