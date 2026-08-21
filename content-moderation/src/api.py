import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException

from . import config
from .storage_client import upload_file, get_result
from .queue_client import send_job


app = FastAPI(title="Content Moderation API")


@app.post("/moderate")
async def moderate(
    file: UploadFile = File(...),
    caption: str = Form(default=""),
):
    # --- Abuse-resistance: validate before doing any real work ---
    if file.content_type not in config.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > config.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail="File too large")

    # --- Store the raw upload in S3 ---
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}"
    upload_file(file_bytes, s3_key, file.content_type)

    # --- Queue the job for the worker ---
    job = {
        "job_id": job_id,
        "s3_key": s3_key,
        "caption": caption,
    }
    send_job(job)

    # --- Respond immediately, don't wait on inference ---
    return {
        "job_id": job_id,
        "status": "queued",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    result = get_result(job_id)
    if result is None:
        return {"job_id": job_id, "status": "processing"}
    return {"job_id": job_id, "status": "done", "result": result}