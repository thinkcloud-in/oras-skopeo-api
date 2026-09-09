#-----------------------------------------This is being used for Production----------------------------------------------------
# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.12.1-slim-bookworm

# Install system dependencies + skopeo (skopeo ships in Debian bookworm's own apt repo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libc-dev \
    libssl-dev \
    libffi-dev \
    skopeo \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install oras CLI (no apt package exists; fetched from the official GitHub release)
ARG ORAS_VERSION=1.3.4
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
        amd64) ORAS_ARCH=amd64 ;; \
        arm64) ORAS_ARCH=arm64 ;; \
        *) echo "Unsupported architecture: $(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/oras.tar.gz \
        "https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_${ORAS_ARCH}.tar.gz"; \
    mkdir -p /tmp/oras-install; \
    tar -zxf /tmp/oras.tar.gz -C /tmp/oras-install; \
    mv /tmp/oras-install/oras /usr/local/bin/oras; \
    chmod +x /usr/local/bin/oras; \
    rm -rf /tmp/oras.tar.gz /tmp/oras-install

# Fail the build immediately (in Jenkins/CI) if either tool didn't install correctly
RUN skopeo --version && oras version

# Set the working directory in the container
WORKDIR /app

RUN pip install --upgrade pip

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies using pip (from requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8009"]
