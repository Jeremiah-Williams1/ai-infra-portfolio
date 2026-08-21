import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from PIL import Image
import io

from . import config
from .storage_client import upload_file, get_result
from .queue_client import send_job

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Content Moderation API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def validate_image_bytes(file_bytes: bytes) -> str:
    """Verify the file is actually a real image by trying to open it,
    rather than trusting the client-reported Content-Type header.
    Returns the real detected format (e.g. 'JPEG', 'PNG')."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # raises if the file is corrupt or not a real image
        return img.format
    except Exception:
        raise HTTPException(status_code=415, detail="File is not a valid image")


@app.post("/moderate")
@limiter.limit("10/minute")
async def moderate(
    request: Request,
    file: UploadFile = File(...),
    caption: str = Form(default=""),
):
    file_bytes = await file.read()

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > config.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail="File too large")

    # Real validation: verify actual bytes, not the client-supplied header
    validate_image_bytes(file_bytes)

    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}"
    upload_file(file_bytes, s3_key, file.content_type)

    job = {
        "job_id": job_id,
        "s3_key": s3_key,
        "caption": caption,
    }
    send_job(job)

    return {
        "job_id": job_id,
        "status": "queued",
    }


@app.get("/status/{job_id}")
@limiter.limit("30/minute")
def get_status(request: Request, job_id: str):
    result = get_result(job_id)
    if result is None:
        return {"job_id": job_id, "status": "processing"}
    return {"job_id": job_id, "status": "done", "result": result}


@app.get("/health")
def health():
    return {"status": "ok"}