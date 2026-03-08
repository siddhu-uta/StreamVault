"""
conftest.py — sets required AWS environment variables before ANY module is imported.
This file is loaded automatically by pytest before collecting any tests.
"""
import os

# AWS credentials (moto doesn't need real ones, but boto3 requires them to be set)
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")

# Lambda environment variables
os.environ.setdefault("QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/000000000000/test-queue")
os.environ.setdefault("TABLE_NAME", "test-events-table")
os.environ.setdefault("BUCKET_NAME", "test-events-bucket")
os.environ.setdefault("ENVIRONMENT", "test")

# Disable X-Ray in all unit tests
os.environ["AWS_XRAY_SDK_ENABLED"] = "false"
