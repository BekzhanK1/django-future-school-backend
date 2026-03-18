#!/usr/bin/env python3
"""
Initialize MinIO bucket for Django media storage.
This script creates the media bucket if it doesn't exist.
"""

import json
import os
import sys
import time
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

def init_minio_bucket():
    """Create MinIO bucket for media files if it doesn't exist."""
    
    # Get environment variables
    endpoint = os.getenv('MINIO_ENDPOINT', 'http://minio:9000')
    access_key = os.getenv('MINIO_ROOT_USER', 'minioadmin')
    secret_key = os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin123')
    bucket_name = os.getenv('MINIO_MEDIA_BUCKET_NAME', 'media')
    
    print(f"Initializing MinIO bucket '{bucket_name}' at {endpoint}")
    print(f"Access key: {access_key}")
    
    # Configure S3 client for MinIO
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'  # MinIO default region
    )
    
    # Retry logic for MinIO startup
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Check if bucket exists
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' already exists")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    s3_client.create_bucket(Bucket=bucket_name)
                    print(f"Bucket '{bucket_name}' created successfully")
                    
                    # Set bucket policy for public read access (optional)
                    # This allows direct access to media files via URL
                    try:
                        policy = {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"AWS": "*"},
                                    "Action": ["s3:GetObject"],
                                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                                }
                            ]
                        }
                        s3_client.put_bucket_policy(
                            Bucket=bucket_name,
                            Policy=json.dumps(policy)
                        )
                        print(f"Public read policy set for bucket '{bucket_name}'")
                    except Exception as policy_error:
                        print(f"Warning: Could not set bucket policy: {policy_error}")
                    
                    return True
                except ClientError as create_error:
                    print(f"Error creating bucket: {create_error}")
                    return False
            elif error_code == '403':
                print(f"Access denied to bucket '{bucket_name}'")
                return False
            else:
                # MinIO might not be ready yet
                if attempt < max_retries - 1:
                    print(f"MinIO not ready (attempt {attempt + 1}/{max_retries}): {error_code}")
                    time.sleep(retry_delay)
                else:
                    print(f"Failed to connect to MinIO after {max_retries} attempts")
                    return False
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                time.sleep(retry_delay)
            else:
                print(f"Failed to connect to MinIO after {max_retries} attempts: {str(e)}")
                return False
    
    return False

if __name__ == '__main__':
    success = init_minio_bucket()
    sys.exit(0 if success else 1)