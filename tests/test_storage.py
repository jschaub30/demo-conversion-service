import os
from pathlib import Path

import pytest
import boto3

from popocr.storage import (create_bucket, download_file_from_s3,
                            remove_bucket, upload_file_to_s3)

# Set the test bucket name and region
TEST_BUCKET_NAME = "test-bucket"
TEST_REGION = "us-east-1"

# Ensure MinIO or AWS credentials are set in environment variables
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

@pytest.fixture(scope="module")
def setup_s3_bucket():
    """
    Fixture to create an S3 bucket for testing and clean up after tests are complete.
    """
    # Create the test bucket
    created = create_bucket(TEST_BUCKET_NAME, region=TEST_REGION)
    assert created is True, "Failed to create test bucket"

    # Run the tests
    yield

    # Clean up the bucket after tests
    removed = remove_bucket(TEST_BUCKET_NAME, region=TEST_REGION)
    assert removed is True, "Failed to remove test bucket"


def test_upload_file_to_s3(setup_s3_bucket, tmpdir):
    """
    Test uploading a file to S3.
    """
    # Create a temporary file to upload
    test_file = tmpdir.join("test_upload.txt")
    test_file.write("This is a test upload file.")

    # Define S3 object name
    s3_object_name = "test_upload.txt"

    # Upload the file
    upload_file_to_s3(str(test_file), TEST_BUCKET_NAME, s3_object_name, region=TEST_REGION)

    # Ensure file is uploaded
    s3_client = boto3.client('s3', endpoint_url=S3_ENDPOINT_URL, 
                             aws_access_key_id=S3_ACCESS_KEY,
                             aws_secret_access_key=S3_SECRET_KEY,
                             region_name=TEST_REGION)
    result = s3_client.head_object(Bucket=TEST_BUCKET_NAME, Key=s3_object_name)
    
    assert result['ResponseMetadata']['HTTPStatusCode'] == 200, "File was not uploaded to S3"


def test_download_file_from_s3(setup_s3_bucket, tmpdir):
    """
    Test downloading a file from S3.
    """
    # Set up a test file and upload it first
    s3_object_name = "test_download.txt"
    test_file_content = "This is a test download file."
    
    # Create a temporary file and upload it
    test_file = tmpdir.join(s3_object_name)
    test_file.write(test_file_content)
    upload_file_to_s3(str(test_file), TEST_BUCKET_NAME, s3_object_name, region=TEST_REGION)

    # Download the file to a new directory
    download_dir = tmpdir.mkdir("downloads")
    download_path = download_file_from_s3(TEST_BUCKET_NAME, s3_object_name, str(download_dir), region=TEST_REGION)

    # Ensure the file exists and the content is correct
    downloaded_content = Path(download_path).read_text()
    assert downloaded_content == test_file_content, "Downloaded content does not match the uploaded file"

