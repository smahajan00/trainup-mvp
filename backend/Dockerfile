FROM python:3.12-slim

WORKDIR /app
ARG TARGETARCH
ARG TORCH_VERSION=2.5.1

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MEDIAPIPE_DISABLE_GPU=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# MediaPipe pulls the GUI OpenCV wheel by default. Replace it with the
# headless contrib build so the backend image does not depend on desktop X11 libs.
# Install Torch before the rest of the requirements so Docker/macOS demo builds
# use CPU-only PyTorch and do not download NVIDIA CUDA dependency packages.
RUN pip install --no-cache-dir --upgrade pip \
    && if [ "$TARGETARCH" = "amd64" ]; then \
        pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}"; \
    else \
        pip install --no-cache-dir "torch==${TORCH_VERSION}"; \
    fi \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "import importlib.metadata as md, torch; bad=sorted(d.metadata['Name'] for d in md.distributions() if d.metadata['Name'].lower().startswith('nvidia-')); assert not bad, f'CUDA packages installed: {bad}'; assert torch.version.cuda is None, f'CUDA torch installed: {torch.version.cuda}'; print(f'CPU-only torch verified: {torch.__version__}')" \
    && pip uninstall -y opencv-contrib-python opencv-python opencv-python-headless \
    && pip install --no-cache-dir opencv-contrib-python-headless==4.13.0.92

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
