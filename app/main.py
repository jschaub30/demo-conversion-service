# main web app

import os
from fastapi import FastAPI, File, UploadFile, HTTPException
import shutil
from popocr import upload_file_to_s3, download_file_from_s3

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

app = FastAPI()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # Use the S3_BUCKET_NAME from the environment variable
    bucket = S3_BUCKET_NAME

    # Save the uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_file_path = temp_file.name

    # Use the original filename as the object key
    object_key = file.filename

    # Upload the temporary file to S3 using the original filename
    try:
        upload_file_to_s3(temp_file_path, bucket, object_key)
    finally:
        # Make sure to delete the temporary file
        os.remove(temp_file_path)

    return {"filename": file.filename, "bucket": bucket, "object_key": object_key}

@app.get("/download")
async def download(bucket: str, key: str):
    if not bucket or not key:
        raise HTTPException(status_code=400, detail="Bucket and key are required.")

    # Call download_file_from_s3 function (to be implemented)
    # file_path = download_file_from_s3(bucket, key, "/path/to/download/dir")
    # return FileResponse(file_path)
    return {"bucket": bucket, "key": key}

