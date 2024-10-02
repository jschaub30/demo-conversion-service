import uuid
import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table_name = "DocumentConversionJobs"
TABLE = dynamodb.Table(table_name)


def lambda_handler(event, context):
    bucket_name = os.environ.get('BUCKET_NAME')
    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    if not bucket_name:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({'message': "Bucket name not set in environment variables"})
        }

    body = event.get('body')

    if isinstance(body, str):
        body = json.loads(body)

    if body is None or 'filename' not in body or 'content_type' not in body:
        return {
            'statusCode': 400,
            "headers": headers,
            'body': json.dumps({'message': "Must provide 'filename' and 'content_type' in body"})
        }
        
    # print(json.dumps(event))
    # print(json.dumps(body))

    if 'job_id' in body:
        job_id = body['job_id']
    else:
        job_id = str(uuid.uuid4())[:8]
    object_key = f"input/{job_id}/{body['filename']}"
    content_type = body["content_type"]
    create_job(job_id, bucket_name, object_key)
    
    s3_client = boto3.client('s3')

    try:
        # Generate the presigned URL
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ContentType': content_type
            },
            ExpiresIn=3600,  # URL expiration time in seconds
            HttpMethod='PUT'
        )
    except Exception as e:
        message = f'Error generating presigned URL: {str(e)}'
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'message': message})
        }
        update_job(job_id, "error", message=message)
    
    result = {
        'presigned_url': presigned_url,
        'job_id': job_id
    }
    return {
        'statusCode': 200,
        "headers": headers,
        'body': json.dumps(result)
    }


def create_job(job_id, bucket_name, object_key, metadata=None):
    s3_url = f"s3://{bucket_name}/{object_key}"
    try:
        item = {
            'job_id': job_id,
            'created_at': datetime.utcnow().isoformat(),
            's3_urls': [s3_url],  # Store input file URL as a list
            'status': 'started',
        }

        if metadata:
            item['metadata'] = metadata  # Add optional metadata field

        response = TABLE.put_item(Item=item)
        logger.info(f"Job {job_id} created successfully")
    except ClientError as e:
        logger.error(f"Error creating job {job_id} record: {e.response['Error']['Message']}")


def update_job(job_id, status, urls=None, message=None, metadata=None):
    try:
        item = {
            'job_id': job_id,
            'created_at': datetime.utcnow().isoformat(),
            'status': status,
        }

        if status == 'success' and urls:
            item['urls'] = urls
        elif message:
            item['message'] = message

        if metadata:
            item['metadata'] = metadata

        response = TABLE.put_item(Item=item)
        logger.info(f"Job {job_id} with status={status!r} updated successfully")
    except ClientError as e:
        logger.error(f"Error updating job record: {e.response['Error']['Message']}")
