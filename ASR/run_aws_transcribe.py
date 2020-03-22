"""AWS Transcribe module initializing client, job status and more."""

import json
import sys
import time
import urllib

import boto3


# try:
#     import config
# except ImportError:
#     import ASR.config as config

# AWS_ACCESS_KEY_ID = config.AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY = config.AWS_SECRET_ACCESS_KEY


def transcribe_job(job_name, job_uri, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY):
    """Transcribe an audio file fetching text and timestamps.

    :param job_name: name of the transcription job
    :type job_name: str
    :param job_uri: S3 file path to an audio file
    :type job_uri: str
    :return: transcript with timestamps and confidences
    :rtype: dict
    """
    transcribe = boto3.client(
        "transcribe",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": job_uri},
        MediaFormat="wav",
        LanguageCode="en-US",
        Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 2},
    )

    while True:
        status = transcribe.get_transcription_job(
            TranscriptionJobName=job_name
        )
        if status["TranscriptionJob"]["TranscriptionJobStatus"] in [
            "COMPLETED",
            "FAILED",
        ]:
            break
        sys.stdout.write("Not ready yet...\r")
        sys.stdout.flush()
        time.sleep(2)

    sys.stdout.write(
        status["TranscriptionJob"]["TranscriptionJobStatus"] + "\n"
    )
    sys.stdout.flush()

    if status["TranscriptionJob"]["TranscriptionJobStatus"] == "FAILED":
        return {
            "jobName": job_name,
            "accountId": "",
            "results": {"transcripts": [], "items": []},
            "status": "FAILED",
        }
    else:
        response = urllib.request.urlopen(
            status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        )
        data = json.loads(response.read())
        return data
