"""
S3 storage functions
"""

import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def get_s3_client(region: str = ""):
    if not region:
        region = "us-east-1"
    if "S3_ACCESS_KEY" in os.environ:
        # Connect to S3 in a local development environment
        return boto3.client(
            "s3",
            endpoint_url=os.environ["S3_ENDPOINT_URL"],
            aws_access_key_id=os.environ["S3_ACCESS_KEY"],
            aws_secret_access_key=os.environ["S3_SECRET_KEY"],
            region_name=region,
            config=boto3.session.Config(signature_version="s3v4"),
        )
    else:
        # Connect to AWS S3 in a production environment
        return boto3.client("s3", region_name=region)


def create_bucket(bucket_name, region: str = ""):
    """
    Create an S3 bucket in a specified region. If a region is not specified, the bucket
    is created in the S3 default region (us-east-1).

    :param bucket_name: Bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :return: True if bucket created, else False
    """
    s3_client = get_s3_client(region)
    try:
        if region is None:
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            location = {"LocationConstraint": region}
            s3_client.create_bucket(
                Bucket=bucket_name, CreateBucketConfiguration=location
            )
    except ClientError as e:
        print(f"Error: {e}")
        return False
    return True


def remove_bucket(bucket_name, region: str = ""):
    """
    Remove an S3 bucket and all its contents.

    :param bucket_name: Name of the S3 bucket to remove.
    :param region: AWS region where the bucket is located. Defaults to 'us-east-1'.
    :return: True if the bucket was successfully removed, False otherwise.
    """
    s3_resource = boto3.resource(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),  # If using MinIO or custom S3
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
        region_name=region if region else "us-east-1",
    )

    bucket = s3_resource.Bucket(bucket_name)

    try:
        # Delete all objects in the bucket
        bucket.objects.all().delete()

        # Now that the bucket is empty, delete the bucket itself
        bucket.delete()
        print(
            f"Bucket '{bucket_name}' and its contents have been removed successfully."
        )
        return True

    except ClientError as e:
        print(f"Error: {e}")
        return False


def upload_file_to_s3(
    file_path: str, bucket_name: str, object_name: str, region: str = ""
):
    """
    Upload a file to an S3 bucket, creating the bucket if it does not exist.

    :param file_path: File to upload
    :param bucket_name: Bucket to upload to
    :param object_name: S3 object name
    :param region: AWS region where the bucket resides
    """
    s3_client = get_s3_client(region)
    try:
        s3_client.upload_file(file_path, bucket_name, object_name)
        print(f"File {file_path} uploaded to {bucket_name}/{object_name}")
    except ClientError as e:
        print(f"Error: {e}")
        raise e


def download_file_from_s3(
    bucket_name: str, object_key: str, download_dir: str, region: str = ""
) -> str:
    """
    Download a file from S3 and return its local path.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The key of the object in the S3 bucket.
        download_dir (str): The directory where the file will be downloaded.
        region (str): The region where the bucket is located.

    Returns:
        str: The path to the downloaded or converted file.
    """
    # Initialize a boto3 client
    s3_client = get_s3_client(region)

    # Construct the download path
    download_path = Path(download_dir) / Path(object_key).name

    # Download the file
    s3_client.download_file(bucket_name, object_key, download_path.as_posix())
    return download_path.as_posix()
