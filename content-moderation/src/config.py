import os
from dotenv import load_dotenv

load_dotenv()

# AWS
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# Upload constraints (abuse-resistance)
MAX_FILE_SIZE_MB = 8
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Decision thresholds
IMAGE_UNSAFE_THRESHOLD = 0.7
IMAGE_REVIEW_THRESHOLD = 0.4
TEXT_TOXIC_THRESHOLD = 0.7