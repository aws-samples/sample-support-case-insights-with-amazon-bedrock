#!/usr/bin/env python3
"""
Simple script to replace <BucketName> placeholders in CloudFormation template
"""

import sys
import re

def update_template(template_path, bucket_name):
    """Replace <BucketName> placeholders with the actual bucket name"""
    
    # Read the template file
    with open(template_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace <BucketName> with the actual bucket name
    # Make sure to preserve indentation
    updated_content = re.sub(r'(S3Bucket:\s*)<BucketName>', r'\1' + bucket_name, content)
    
    # Write the updated template
    output_path = template_path.replace(".yaml", "-updated.yaml")
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)
    
    print(f"Updated template saved to {output_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update-bucket-name.py <template_path> <bucket_name>")
        print("Example: python update-bucket-name.py cloudformation/case-insights.yaml my-deployment-bucket")
        sys.exit(1)
    
    template_path = sys.argv[1]
    bucket_name = sys.argv[2]
    
    update_template(template_path, bucket_name)
    print("Template updated successfully")