import os

# AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "content-moderation-uploads")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")  # filled in once queue exists

# Upload constraints (abuse-resistance)
MAX_FILE_SIZE_MB = 8
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Decision thresholds
IMAGE_UNSAFE_THRESHOLD = 0.7   # above this -> block
IMAGE_REVIEW_THRESHOLD = 0.4   # above this -> flag for human review
TEXT_TOXIC_THRESHOLD = 0.7