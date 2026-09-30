# syntax=docker/dockerfile:1

# ============================================================
# Stage 1: builder
#   Installs dependencies into an isolated venv. This stage's
#   build tools, caches, and layers never end up in the final image.
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# IMPORTANT: pip install torch (no index) pulls PyPI's default Linux wheel,
# which bundles the full CUDA toolkit (~4-5GB of nvidia-* packages) even
# if you never touch a GPU. For a CPU-serving image, install from
# PyTorch's own CPU-only index instead - this is the single biggest
# lever for image size here.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 2: runtime
#   Only the venv and application code make it in - no compilers,
#   no pip cache, no build-time-only files.
# ============================================================
FROM python:3.11-slim

# Never run the server as root
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Build context is the project root: docker build -f docker/Dockerfile .
COPY model/model.py model/inference.py ./
COPY model/model_artifacts/ ./model_artifacts/

ENV MODEL_PATH=/app/model_artifacts/model.pt
ENV PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

# Kubernetes will do its own liveness/readiness probing later (step 3),
# but HEALTHCHECK is still useful for plain `docker run` and for
# container runtimes/orchestrators that respect it directly.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python3", "-m", "uvicorn", "inference:app", "--host", "0.0.0.0", "--port", "8000"]
