import time
import json
import traceback
from datetime import datetime, timezone

from . import config
from .storage_client import download_file, upload_result
from .queue_client import poll_jobs, delete_job
from .models import image_model, text_model
from .decision import evaluate


def process_job(job: dict) -> dict:
    job_id = job["job_id"]
    s3_key = job["s3_key"]
    caption = job.get("caption", "")

    image_bytes = download_file(s3_key)
    image_result = image_model.predict(image_bytes)

    text_result = text_model.predict(caption) if caption.strip() else None

    result = evaluate(image_result, text_result)
    result["job_id"] = job_id
    result["processed_at"] = datetime.now(timezone.utc).isoformat()

    return result


def run():
    print("Worker started, polling for jobs...")

    # Load models once at startup, not per-job
    image_model.load_model()
    text_model.load_model()
    print("Models loaded. Ready.")

    while True:
        messages = poll_jobs()

        if not messages:
            continue  # long polling already waited; loop straight back around

        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            try:
                job = json.loads(message["Body"])
                print(f"Processing job {job['job_id']}...")

                result = process_job(job)
                upload_result(job["job_id"], result)

                delete_job(receipt_handle)
                print(f"Job {job['job_id']} done -> {result['final_decision']}")

            except Exception as e:
                # Don't delete the message -> it becomes visible again after
                # the visibility timeout and gets retried. After enough
                # retries, SQS redrive policy moves it to the DLQ (set on
                # the queue itself, not here).
                print(f"Job failed: {e}")
                traceback.print_exc()


if __name__ == "__main__":
    run()