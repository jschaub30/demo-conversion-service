"""
Convert image and PDF files into text/structured text

Requires tesseract and poppler lambda layers
- see https://github.com/jschaub30/lambda-layers
"""
import boto3
import os
import json
import tempfile
import logging
from pathlib import Path
import subprocess
from subprocess import TimeoutExpired, CalledProcessError
from typing import Dict, Optional, Any
from datetime import datetime
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table_name = "DocumentConversionJobs"
TABLE = dynamodb.Table(table_name)

s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class SystemCallError(Exception):
    # Raised when calling a system command
    pass


def run_command_with_timeout(command, timeout):
    """
    Runs a system command with a specified timeout. Raises SystemCallError if the command
    fails or returns a non-zero exit status.

    Parameters:
    - command (list): The command to execute and its arguments as a list.
    - timeout (int): The timeout in seconds.

    Returns:
    - The output of the command if successful.

    Raises:
    - SystemCallError: If the command fails, times out, or returns a non-zero exit status.
    """
    logger.info(f"Running command: {command}")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=timeout
        )
        logger.info(result)
        return result.stdout
    except TimeoutExpired as e:
        raise SystemCallError(
            f"Command '{' '.join(command)}' timed out after {timeout} seconds"
        ) from e
    except CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else e.stdout.strip()
        raise SystemCallError(
            f"Command '{' '.join(command)}' failed with exit status {e.returncode}: {error_message}"
        ) from e
    except Exception as e:
        raise SystemCallError(
            f"An error occurred while executing command '{' '.join(command)}': {str(e)}"
        ) from e


def convert_image_tesseract(
    image_filename: str, output_base_path: Optional[Path] = None, timeout: int = 60
) -> str:
    """
    Converts an image file to a PDF using Tesseract OCR.

    Args:
        image_path (str): The path to the image file to convert.
        output_base_path (str, optional): The basename where the output files should be saved.
        If not specified, the PDF will be saved in the same location as the image.
        timeout (int): The timeout in seconds for the Tesseract command.

    Returns:
        dict: dict with {extension: local_fn} e.g. {'xml': '/tmp/img.xml'}

    Raises:
        SystemCallError: If the Tesseract command fails, times out, or returns a non-zero exit code.
    """
    image_path_obj = Path(image_filename)

    if output_base_path is None:
        output_base_path = image_path_obj.with_suffix("")
    else:
        output_base_path = Path(output_base_path).with_suffix("")

    # Tesseract adds ".pdf" to the output base name itself
    command = ["tesseract", image_filename, str(output_base_path), "pdf", "hocr", "txt"]

    # Execute the command with a timeout
    run_command_with_timeout(command, timeout)

    output = {}
    for ext in ('.pdf', '.txt', '.hocr'):
        local_fn_pth = str(output_base_path.with_suffix(ext))
        if ext == '.hocr':
            key = 'html'
        else:
            key = ext.strip('.')
        output[key] = local_fn_pth
    return output


def convert_pdf_poppler(
    pdf_filename: str, first_page: int = 1, last_page: int = 10, timeout: int = 60
) -> str:
    """
    Converts a PDF file to text and html files using the Poppler `pdftotext` command.

    Args:
        pdf_filename (str): The path to the PDF file to convert.
        first_page (int): First page to convert (default=1)
        last_page (int): Last page to convert (default=10)
        timeout (int): The timeout in seconds for the `pdftotext` command.

    Returns:
        dict: The path to the generated text file.
    """
    output = {}
    
    # TXT output
    for ext in ('.txt', '.html'):
        output_filename = str(Path(pdf_filename).with_suffix(ext))
        command = ["pdftotext"]
        if ext == ".html":
            command.extend(['-bbox-layout'])
    
        command.extend(["-f", str(first_page), "-l", str(last_page)])
        command.extend([pdf_filename, output_filename])
        
        try:
            run_command_with_timeout(command, timeout)
        except Exception as e:
            raise SystemCallError(f"Failed to convert {pdf_filename} to text: {str(e)}")
        output[ext.strip('.')] = output_filename

    return output
        

def process_file(bucket_name: str, object_key: str, job_id, config: Dict[str, Any]):
    """
    Download a file from S3. 
    
    Convert to txt, pdf and xml (hocr format)

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The key of the object in the S3 bucket.
        config (Dict[str, Any]): Configuration options
    """
    logger.info(f"Start processing {object_key}")
    try:
        head_response = s3.head_object(Bucket=bucket_name, Key=object_key)
        content_type = head_response['ContentType']

        # Check if the content type is allowed (image or PDF)
        if not (
            content_type == 'application/pdf' or content_type.startswith('image')
            ):
            message = f"File {object_key} is not an image or PDF, skipping processing."
            update_job(job_id, "error", message=message)
            logger.error(message)
            return {
                'statusCode': 400,
                'body': message
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_filename = f"{temp_dir}/{os.path.basename(object_key)}"
            logger.info(f"Downloading from s3: {input_filename}")
            s3.download_file(bucket_name, object_key, input_filename)

            output_prefix = str(Path(object_key.replace('input', 'output', 1)).with_suffix(""))
            result = {}
            if content_type.startswith('image'):
                # tesseract can do it all
                output = convert_image_tesseract(input_filename)
            else:
                output = convert_pdf_poppler(input_filename)

            # upload output files to S3
            for fmt, local_fn_pth in output.items():
                object_key = f"{output_prefix}.{fmt}"
                logger.info(f"Uploading {local_fn_pth!r} to s3://{bucket_name}/{object_key}")
                s3.upload_file(local_fn_pth, bucket_name, object_key)
                result[fmt] = object_key
        return result

    except Exception as e:
        message = f"Failed to process the file: {str(e)}"
        update_job(job_id, "error", message=message)
        logger.error(message)
        raise Exception(message)
    return result


def lambda_handler(event, context):
    # print(json.dumps(event))  # use to create test cases
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']
    job_id = object_key.split("input/")[1].split("/")[0]
    result = process_file(bucket_name, object_key, job_id, None)
    expiration_time_sec = 172800  # 2 days
    urls = {}
    try:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expiration_time_sec,
        )
        urls['input'] = url
        for ext, object_key in result.items():
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key,
                },
                ExpiresIn=expiration_time_sec,
            )
            urls[ext] = url
        update_job(job_id, "success", urls=urls, message=None, metadata=None)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Error generating presigned URL: {str(e)}'})
        }
    return urls


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
