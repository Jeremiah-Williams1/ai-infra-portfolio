# Content Moderation Service

A real-time content moderation pipeline: a client uploads an image + optional
caption, the system scores both for unsafe content using pretrained models,
and returns a pass/flag/block decision — without blocking the client while
inference runs.

Built as Project 1 of a broader AI infrastructure portfolio. Focus is the
**infrastructure and deployment layer** around pretrained models, not model
training.

## Architecture

![Content Moderation Architecture](docs/architecture.png)

**Flow:**
1. Client `POST /moderate`s an image + caption to the FastAPI service
2. API validates the upload, stores it in S3, pushes a job onto SQS, and
   responds immediately with a `job_id` — no waiting on inference
3. A separate worker process long-polls SQS, pulls the image from S3
4. Worker runs two models: an NSFW image classifier (GPU) and a text
   toxicity classifier (CPU, isolated in its own subprocess — see below)
5. Worker combines both scores into a final decision, writes the result to
   S3, deletes the SQS message on success
6. Client polls `GET /status/{job_id}` until the result is ready

The API and worker are deliberately separate processes — a slow inference
call should never block the API from accepting the next upload, and each
scales independently (API scales with request volume, worker scales with
queue depth).

## Stack

- **API:** FastAPI + Uvicorn
- **Queue:** AWS SQS (standard queue, long polling, dead-letter queue after
  3 failed receives)
- **Storage:** AWS S3 (`uploads/` for raw files, `results/` for decisions)
- **Compute:** AWS EC2 `g4dn.xlarge` (single T4 GPU)
- **Image model:** `opennsfw2` (TF2 implementation of Yahoo's Open-NSFW),
  runs on GPU
- **Text model:** `unitary/toxic-bert` via HuggingFace `transformers`, runs
  CPU-only, in an isolated subprocess (see Decisions below)
- **Rate limiting:** `slowapi`, per-client-IP, tiered by endpoint cost

## Decision logic

Two models produce independent scores; the final decision is
**worst-of-both-wins**: if either the image or the caption crosses its
threshold, the stricter result applies. A clean image with a toxic caption
still gets blocked, and vice versa.

This was a deliberate choice over a weighted-average approach. Averaging is
arguably more "accurate" to overall severity, but it allows a moderately
unsafe image to be diluted by a clean caption and pass through — a false
pass is more expensive than a false block in a moderation system, so the
conservative default was chosen on purpose.

Thresholds are centralized in `src/config.py`, not scattered through logic,
since they're the piece most likely to need tuning after seeing real
output.

## Abuse-resistance

Someone will specifically try to break a moderation system, so this was
treated as a real design surface, not boilerplate:

- **File size limit** enforced before any S3/GPU cost is incurred
- **Real content validation, not header trust** — the API opens every
  upload with Pillow and calls `.verify()` rather than trusting the
  client-supplied `Content-Type` header, which can be spoofed
- **Per-IP rate limiting**, tiered: 10/min on the expensive upload endpoint,
  30/min on the cheap status-check endpoint
- **SQS dead-letter queue** — a message that fails processing 3 times moves
  to a DLQ instead of retrying forever
- **Adversarial testing performed:** borderline images (swimwear — correctly
  passed), more explicit images (correctly blocked), and a safe image with a
  toxic caption (correctly blocked on the text signal alone) — confirming
  the worst-of-both-wins logic actually triggers as designed at real
  decision boundaries

**Known limitation:** rate limiting is in-memory and per-process. If this
API were scaled horizontally behind a load balancer, each instance would
track limits independently — a real gap, and the documented next step would
be Redis-backed shared limit storage.

## A real debugging story: TensorFlow + PyTorch in one process

The worker loads two models from two different ML frameworks: TensorFlow
(image) and PyTorch, via `transformers` (text). Loading both into the same
process caused a hard segfault — not a catchable Python exception, since the
crash happened inside compiled C/CUDA libraries below Python's error
handling.

Root cause: both frameworks initialize their own CUDA context and bundle
their own OpenMP runtime; having both active in one process is a known
source of low-level conflicts.

**Fix:** the text model now runs in an isolated `subprocess`, called via
argv/stdout, rather than being imported into the worker's main process. This
enforces the GPU/CPU split cleanly (image model owns the GPU, text model is
fully invisible to CUDA) and means a crash in one model can't take down the
whole worker — a real process-isolation pattern, not just a workaround.

Trade-off: the text model reloads on every job instead of staying warm in
memory, which costs latency. A future optimization would be a small
long-running subprocess server instead of spawn-per-call.

Also hit along the way: TensorFlow couldn't see the GPU at all initially,
because `pip install tensorflow[and-cuda]` places CUDA libraries inside
`site-packages/nvidia/`, not a system library path — `LD_LIBRARY_PATH` had
to be explicitly extended to include them, then baked into the conda env's
activation script so it persists across sessions.

## Running it

```bash
conda create -n content-moderation python=3.11
conda activate content-moderation
pip install -r requirements.txt
cp .env.example .env   # fill in AWS_REGION, S3_BUCKET, SQS_QUEUE_URL
```

Two separate processes, run in parallel:

```bash
# Terminal 1
python -m src.worker

# Terminal 2
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

```bash
curl -X POST http://localhost:8000/moderate \
  -F "file=@test.jpg" \
  -F "caption=some caption"

curl http://localhost:8000/status/<job_id>
```

## What I'd do next

- Redis-backed rate limiting for horizontal scaling
- Presigned S3 upload URLs, so raw bytes never route through the API
  process at all
- Warm subprocess pool for the text model instead of spawn-per-call
- KEDA-style autoscaling of the worker based on SQS queue depth
