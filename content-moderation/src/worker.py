import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import time
import json
import subprocess
import traceback
from datetime import datetime, timezone

from . import config
from .storage_client import download_file, upload_result
from .queue_client import poll_jobs, delete_job
from .models import image_model
from .decision import evaluate


def predict_text_isolated(text: str) -> dict:
    result = subprocess.run(
        ["python", "-m", "src.models.text_model_runner", text],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"text_model subprocess failed: {result.stderr}")
    return json.loads(result.stdout.strip())


def process_job(job: dict) -> dict:
    job_id = job["job_id"]
    s3_key = job["s3_key"]
    caption = job.get("caption", "")

    image_bytes = download_file(s3_key)
    image_result = image_model.predict(image_bytes)

    text_result = predict_text_isolated(caption) if caption.strip() else None

    result = evaluate(image_result, text_result)
    result["job_id"] = job_id
    result["processed_at"] = datetime.now(timezone.utc).isoformat()

    return result


def run():
    print("Worker started, polling for jobs...")

    image_model.load_model()
    print("Image model loaded. Ready.")
    # text_model loads inside its own subprocess, per call -- not preloaded here

    while True:
        messages = poll_jobs()

        if not messages:
            continue

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
                print(f"Job failed: {e}")
                traceback.print_exc()


if __name__ == "__main__":
    run()