async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    const statusMessage = document.getElementById('statusMessage');
    const fileLinks = document.getElementById('fileLinks');
    fileLinks.innerHTML = '';

    if (!file) {
        statusMessage.textContent = 'Please select a file to upload.';
        return;
    }

    const filename = file.name;
    const contentType = file.type || 'application/octet-stream';

    try {
        // Call the Lambda function to get the presigned URL
        statusMessage.textContent = 'Getting presigned URL to upload file...';
        const lambdaResponse = await fetch('https://m2t7qwove4.execute-api.us-west-2.amazonaws.com/dev/url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                content_type: contentType
            })
        });

        if (!lambdaResponse.ok) {
            statusMessage.textContent = 'Failed to get presigned URL';
            throw new Error('Failed to get presigned URL');
        }

        const lambdaData = await lambdaResponse.json();
        const presignedUrl = lambdaData.presigned_url;
        const jobId = lambdaData.job_id;

        // Upload the file to S3 using the presigned URL
        statusMessage.textContent = 'Uploading file...';
        const uploadResponse = await fetch(presignedUrl, {
            method: 'PUT',
            headers: {
                'Content-Type': contentType
            },
            body: file
        });

        if (!uploadResponse.ok) {
            throw new Error('Failed to upload file to S3');
        }

        statusMessage.textContent = 'File uploaded successfully. Checking job status...';

        // Start polling the job status
        checkJobStatus(jobId);
    } catch (error) {
        console.error('Error:', error);
        statusMessage.textContent = 'Error uploading file: ' + error.message;
    }
}

async function checkJobStatus(jobId, elapsedTime) {
    const statusMessage = document.getElementById('statusMessage');
    const fileLinks = document.getElementById('fileLinks');
    const pollInterval = 5000; // Poll every 5 seconds
    const maxPollingTime = 300000; // Maximum polling time of 5 minutes (300,000 ms)

    // Stop polling if the elapsed time exceeds 5 minutes
    if (elapsedTime >= maxPollingTime) {
        statusMessage.textContent = 'Polling stopped after 5 minutes. Please try again later.';
        return;
    }

    try {
        const statusResponse = await fetch(`https://m2t7qwove4.execute-api.us-west-2.amazonaws.com/dev/job?job_id=${jobId}`);
        if (!statusResponse.ok) {
            throw new Error('Failed to check job status');
        }

        const statusData = await statusResponse.json();

        if (statusData.status === 'success') {
            statusMessage.textContent = 'Job completed successfully. Here are your files:';

            // Clear previous links
            fileLinks.innerHTML = '';

            // Iterate over the URLs and create links
            for (const [key, url] of Object.entries(statusData.urls)) {
                const link = document.createElement('a');
                link.href = url;
                link.textContent = `${key.toUpperCase()} file`;
                link.target = '_blank';
                fileLinks.appendChild(link);
                fileLinks.appendChild(document.createElement('br'));
            }
        } else if (statusData.status === 'started') {
            if (statusMessage.textContent !== 'Job started successfully. Please wait...') {
                statusMessage.textContent = 'Job started successfully. Please wait...';
            }
            setTimeout(() => checkJobStatus(jobId, elapsedTime + pollInterval), pollInterval);
        } else if (statusData.status === 'error') {
            statusMessage.textContent = statusData.message;
        } else {
            // If the job is still processing (other statuses)
            if (statusMessage.textContent !== 'Job is in progress...') {
                statusMessage.textContent = 'Job is in progress...';
            }
            setTimeout(() => checkJobStatus(jobId, elapsedTime + pollInterval), pollInterval);
        }
    } catch (error) {
        console.error('Error:', error);
        statusMessage.textContent = 'Error checking job status: ' + error.message;
    }
}
