import json
import boto3
from . import config

sqs = boto3.client("sqs", region_name=config.AWS_REGION)

def send_job(job: dict) -> None:
    sqs.send_message(
        QueueUrl=config.SQS_QUEUE_URL,
        MessageBody=json.dumps(job),
    )

def poll_jobs(max_messages: int = 5, wait_seconds: int = 20):
    response = sqs.receive_message(
        QueueUrl=config.SQS_QUEUE_URL,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_seconds,  # long polling
    )
    return response.get("Messages", [])

def delete_job(receipt_handle: str) -> None:
    sqs.delete_message(
        QueueUrl=config.SQS_QUEUE_URL,
        ReceiptHandle=receipt_handle,
    )