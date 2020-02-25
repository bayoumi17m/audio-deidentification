"""Uploading audio files to an S3 bucket on AWS."""
import logging
import boto3
from botocore.exceptions import ClientError

import config


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket.

    :param file_name: File to upload
    :type file_name: str
    :param bucket: Bucket to upload to
    :type bucket: str
    :param object_name: S3 Object name. If not specified, defaults to file_name
    :type object_name: Optional[str]
    :return: True if file was uploaded, else False
    :rtype: boolean
    """
    if object_name is None:
        object_name = file_name
    
    # Upload the file
    s3_client boto3.client("s3",
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        config.AWS_SECRET_ACCESS_KEY
    )
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True