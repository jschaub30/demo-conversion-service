import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.resource('dynamodb')
table_name = "DocumentConversionJobs"
TABLE = dynamodb.Table(table_name)

def query_records_by_job_id(job_id):
    """ query records by job_id """
    try:
        # Query the table by the job_id (Partition Key)
        response = TABLE.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('job_id').eq(job_id)
        )
        # Return the records found
        logger.info(type(response))
        logger.info(response)
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying job records: {e.response['Error']['Message']}")
        return None


def lambda_handler(event, context):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    # logger.debug(json.dumps(event, indent=2))
    query_params = event.get('queryStringParameters')

    if not query_params or not query_params.get('job_id'):
        return {
            'statusCode': 400,
            "headers": headers,
            'body': json.dumps({'message': "Must provide 'job_id' as query parameter"})
        }

    job_id = query_params.get('job_id')

    records = query_records_by_job_id(job_id)
    
    if records:
        status = None
        started = None
        completed = None
        url = None
        urls = None
        message = None
        
        for record in records:
            if record["status"] == "started":
                if status is None:
                    status = "started"
                    started = record["created_at"]
                    url = record['url']
            elif record["status"] == "success":
                status = "success"
                completed = record["created_at"]
                urls = record.get('urls')
            elif record["status"] == "error":
                status = "error"
                completed = record["created_at"]
                message = record.get('message', 'No error message provided')
    
        return {
            'statusCode': 200,
            "headers": headers,
            "body": json.dumps({
                "job_id": job_id,
                "status": status,
                "message": message,
                "started": started,
                "completed": completed,
                "input": url,
                "urls": urls
            })
        }
    else:
        return {
            'statusCode': 200,
            "headers": headers,
            "body": json.dumps({'message': f"Job {job_id!r} not found"})
        }
