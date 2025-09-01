#!/bin/bash
# AWS Case Insights - Lambda Packaging Script
# This script packages all Lambda functions and uploads them to an S3 bucket

# Check if deployment bucket parameter is provided
if [ -z "$1" ]; then
    echo "Error: Deployment bucket name is required"
    echo "Usage: $0 <deployment-bucket> [region]"
    exit 1
fi

# Configuration
DEPLOYMENT_BUCKET="$1"
REGION="${2:-us-east-1}"  # Default to us-east-1 if not specified

echo "Packaging Lambda functions and uploading to s3://$DEPLOYMENT_BUCKET in $REGION"

# Check if bucket exists, create if it doesn't
if ! aws s3 ls "s3://$DEPLOYMENT_BUCKET" --region "$REGION" > /dev/null 2>&1; then
    echo "Bucket does not exist. Creating bucket s3://$DEPLOYMENT_BUCKET in $REGION..."
    if ! aws s3 mb "s3://$DEPLOYMENT_BUCKET" --region "$REGION"; then
        echo "Error creating bucket. Exiting."
        exit 1
    fi
    
    # Apply security settings to the bucket
    echo "Applying security settings to the bucket..."
    
    # Block public access
    aws s3api put-public-access-block \
      --bucket "$DEPLOYMENT_BUCKET" \
      --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
      --region "$REGION"
    å
    # Enable bucket versioning
    aws s3api put-bucket-versioning \
      --bucket "$DEPLOYMENT_BUCKET" \
      --versioning-configuration Status=Enabled \
      --region "$REGION"
    
    # Enable server-side encryption
    aws s3api put-bucket-encryption \
      --bucket "$DEPLOYMENT_BUCKET" \
      --server-side-encryption-configuration '{
        "Rules": [
          {
            "ApplyServerSideEncryptionByDefault": {
              "SSEAlgorithm": "AES256"
            }
        ]
      }' \
      --region "$REGION"
    
    # Get account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Create bucket policy that restricts access to the account
    aws s3api put-bucket-policy \
      --bucket "$DEPLOYMENT_BUCKET" \
      --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
          {
            \"Sid\": \"RestrictToAccount\",
            \"Effect\": \"Deny\",
            \"Principal\": \"*\",
            \"Action\": \"s3:*\",
            \"Resource\": [
              \"arn:aws:s3:::$DEPLOYMENT_BUCKET\",
              \"arn:aws:s3:::$DEPLOYMENT_BUCKET/*\"
            ],
            \"Condition\": {
              \"StringNotEquals\": {
                \"aws:PrincipalAccount\": \"$ACCOUNT_ID\"
              }
            }
          }
        ]
      }" \
      --region "$REGION"
    
    echo "Security settings applied to the bucket."
fi

# Package Lambda functions
LAMBDA_FUNCTIONS=(
    "account-lookup"
    "account-reader"
    "case-annotation"
    "case-cleanup"
    "case-retrieval"
    "start-step-function"
    "step-case-summary"
    "step-lifecycle-analysis"
    "step-rca-analysis"
    "step-update-case-metadata"
)

for func in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "Packaging $func..."
    
    # Create temporary directory
    mkdir -p package
    
    # Install dependencies
    python -m pip install -r "src/lambda/$func/requirements.txt" -t package/
    
    # Copy function code (only app.py to avoid conflicts)
    cp "src/lambda/$func/app.py" package/
    
    # Copy common utilities if needed
    if [ -d "src/lambda/common" ]; then
        cp -r "src/lambda/common" package/
    fi
    
    # Create ZIP file
    (cd package && zip -r "../$func.zip" .) || {
        echo "Error: Failed to create ZIP file for $func"
        exit 1
    }
    
    # Upload to S3
    aws s3 cp "$func.zip" "s3://$DEPLOYMENT_BUCKET/$func.zip" --region "$REGION"
    
    # Clean up
    rm -rf package
    rm "$func.zip"
    
    echo "Successfully packaged and uploaded $func"
done

# Package templates layer
echo "Packaging templates layer..."
mkdir -p template-layer/templates
cp src/templates/*.txt template-layer/templates/
(cd template-layer && zip -r ../template-layer.zip .) || {
    echo "Error: Failed to create template-layer ZIP file"
    exit 1
}
aws s3 cp template-layer.zip "s3://$DEPLOYMENT_BUCKET/template-layer.zip" --region "$REGION"
rm -rf template-layer
rm template-layer.zip

echo "All Lambda functions and layers packaged and uploaded to S3"

# Generate CloudFormation template update instructions
echo ""
echo "Next steps:"
echo "1. Update the CloudFormation template to use your packaged Lambda functions"
echo "2. Replace <BucketName> in cloudformation/case-insights.yaml with: $DEPLOYMENT_BUCKET"
echo "3. Deploy the CloudFormation template with the updated bucket name"
echo ""
echo "The template already includes the TemplateLayer and all necessary references."