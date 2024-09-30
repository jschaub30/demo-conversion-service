import json
import boto3
import os

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

    filename = body["filename"]
    content_type = body["content_type"]
    
    s3_client = boto3.client('s3')

    try:
        # Generate the presigned URL
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': filename,
                'ContentType': content_type
            },
            ExpiresIn=3600,  # URL expiration time in seconds
            HttpMethod='PUT'
        )
    except Exception as e:
        return {
            'statusCode': 500,
            "headers": headers,
            'body': json.dumps({'message': f'Error generating presigned URL: {str(e)}'})
        }

    # Return the presigned URL
    return {
        'statusCode': 200,
        "headers": headers,
        'body': json.dumps({'presigned_url': presigned_url})
    }
