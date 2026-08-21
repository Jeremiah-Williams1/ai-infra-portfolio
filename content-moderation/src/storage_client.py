import boto3
import json
from . import config

s3 = boto3.client("s3", region_name=config.AWS_REGION)

def upload_file(file_bytes: bytes, key: str, content_type: str) -> str:
    s3.put_object(
        Bucket=config.S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key

def download_file(key: str) -> bytes:
    obj = s3.get_object(Bucket=config.S3_BUCKET, Key=key)
    return obj["Body"].read()


def upload_result(job_id: str, result: dict) -> str:
    key = f"results/{job_id}.json"
    s3.put_object(
        Bucket=config.S3_BUCKET,
        Key=key,
        Body=json.dumps(result),
        ContentType="application/json",
    )
    return key

def get_result(job_id: str) -> dict | None:
    key = f"results/{job_id}.json"
    try:
        obj = s3.get_object(Bucket=config.S3_BUCKET, Key=key)
        return json.loads(obj["Body"].read())
    except s3.exceptions.NoSuchKey:
        return None