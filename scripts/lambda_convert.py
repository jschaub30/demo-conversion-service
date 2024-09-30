"""
Convert image and PDF files into text and/or structured text
"""
import boto3
import os
import json
import tempfile
from pathlib import Path
import subprocess
from subprocess import TimeoutExpired, CalledProcessError
from typing import Dict, Optional, Any

s3 = boto3.client('s3')

class SystemCallError(Exception):
    pass


class InvalidFileTypeError(Exception):
    """Exception raised for invalid file types."""

    pass


class ConversionOptions:
    def __init__(self, options: Optional[Dict[str, Any]] = None):
        if options is None:
            options = {}

        valid_keys = {"first_page", "last_page", "output_format"}
        valid_formats = {"xml", "text"}

        for key in options.keys():
            if key not in valid_keys:
                raise ValueError(f"Invalid option: {key}")

        self.first_page = options.get("first_page", 1)
        self.last_page = options.get("last_page", 1)
        self.output_format = options.get("output_format", "xml")  # Default to XML

        if self.output_format not in valid_formats:
            raise ValueError(f"Invalid output format: {self.output_format}")


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
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=timeout
        )
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


def convert_image_to_pdf(
    image_path: str, output_pdf_path: Optional[str] = None, timeout: int = 60
) -> str:
    """
    Converts an image file to a PDF using Tesseract OCR.

    Args:
        image_path (str): The path to the image file to convert.
        output_pdf_path (str, optional): The path where the output PDF should be saved.
        If not specified, the PDF will be saved in the same location as the image.
        timeout (int): The timeout in seconds for the Tesseract command.

    Returns:
        str: The path to the generated PDF file.

    Raises:
        SystemCallError: If the Tesseract command fails, times out, or returns a non-zero exit code.
    """
    image_path_obj = Path(image_path)

    if output_pdf_path is None:
        output_pdf_path = image_path_obj.with_suffix(".pdf").as_posix()
    else:
        output_pdf_path = Path(output_pdf_path).as_posix()

    # Tesseract adds ".pdf" to the output base name itself
    output_base = Path(output_pdf_path).with_suffix("")

    command = ["tesseract", image_path, output_base, "pdf"]

    # Execute the command with a timeout
    run_command_with_timeout(command, timeout)

    return output_pdf_path


def pdf_to_text(
    pdf_filename: str, conversion_options: ConversionOptions, timeout: int = 30
) -> str:
    """
    Converts a PDF file to a text file using the Poppler `pdftotext` command.

    Args:
        pdf_filename (str): The path to the PDF file to convert.
        conversion_options (ConversionOptions): Options specifying the conversion details.
        timeout (int): The timeout in seconds for the `pdftotext` command.

    Returns:
        str: The path to the generated text file.
    """
    output_filename = pdf_filename.rsplit(".", 1)[0] + ".txt"
    command = ["pdftotext"]

    if conversion_options.first_page:
        command.extend(["-f", str(conversion_options.first_page)])

    if conversion_options.last_page:
        command.extend(["-l", str(conversion_options.last_page)])

    command.extend([pdf_filename, output_filename])

    try:
        run_command_with_timeout(command, timeout)
        return output_filename
    except Exception as e:
        raise SystemCallError(f"Failed to convert {pdf_filename} to text: {str(e)}")


def pdf_to_xml(
    pdf_filename: str, conversion_options: ConversionOptions, timeout: int = 30
) -> str:
    """
    Converts a PDF file to an XML file using the Poppler `pdftohtml` command.

    Args:
        pdf_filename (str): The path to the PDF file to convert.
        conversion_options (ConversionOptions): Options specifying the conversion details.
        timeout (int): The timeout in seconds for the `pdftohtml` command.

    Returns:
        str: The path to the generated XML file.

    Raises:
        SystemCallError: If the `pdftohtml` command fails, times out, or returns a non-zero
                         exit status.
    """
    output_filename = str(Path(pdf_filename).with_suffix(".xml"))
    command = ["pdftohtml", "-xml"]

    if conversion_options.first_page:
        command.extend(["-f", str(conversion_options.first_page)])

    if conversion_options.last_page:
        command.extend(["-l", str(conversion_options.last_page)])

    command.extend(
        [pdf_filename, output_filename.replace(".xml", "")]
    )  # pdftohtml adds .xml

    try:
        # Run the command with a timeout
        run_command_with_timeout(command, timeout)
        return output_filename
    except Exception as e:
        raise SystemCallError(f"Failed to convert {pdf_filename} to XML: {str(e)}")


def process_file(bucket_name: str, object_key: str, config: Dict[str, Any]):
    """
    Download a file from S3. If it's an image or PDF, convert to text and xml

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_key (str): The key of the object in the S3 bucket.
        config (Dict[str, Any]): Configuration options
    """
    print(f"Start processing {object_key}")
    try:
        head_response = s3.head_object(Bucket=bucket_name, Key=object_key)
        content_type = head_response['ContentType']

        # Check if the content type is allowed (image or PDF)
        if not (
            content_type == 'application/pdf' or content_type.startswith('image')
            ):
            print(f"Conversion to TXT and XML not enabled for {content_type!r} files")
            return {
                'statusCode': 400,
                'body': json.dumps(f"File {object_key} is not an image or PDF, skipping processing.")
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file_path = f"/{temp_dir}/{os.path.basename(object_key)}"
            s3.download_file(bucket_name, object_key, input_file_path)
            # Convert to PDF first if it's an image
            if content_type.startswith('image'):
                input_file_path = convert_image_to_pdf(input_file_path)
            if not config:
                config = {}
            if False:
                config["output_format"] = "xml"
                conversion_options = ConversionOptions(config)
                xml_output_path = pdf_to_xml(
                    input_file_path, conversion_options
                )
                object_xml_key = str(Path(object_key.replace('input', 'output', 1)).with_suffix('.xml'))
                s3.upload_file(xml_output_path, bucket_name, object_txt_key)
            config["output_format"] = "text"
            conversion_options = ConversionOptions(config)
            txt_output_path = pdf_to_text(
                input_file_path, conversion_options
            )
            object_txt_key = str(Path(object_key.replace('input', 'output', 1)).with_suffix('.txt'))
            s3.upload_file(txt_output_path, bucket_name, object_txt_key)


    except Exception as e:
        raise Exception(f"Failed to process the file: {str(e)}")
    return {"output_txt_key": object_txt_key}


def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']
    result = process_file(bucket_name, object_key, None)
    print(json.dumps(result))
    return result