"""
Upload raw harvested OpenAlex JSON payloads to MinIO object storage (ELT pipeline).

Usage:
    python backend/upload_minio.py
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
RAW_PAPERS_PATH = BASE_DIR / "data" / "raw" / "papers_raw.json"


def _load_env() -> None:
    env_path = BACKEND_DIR / ".env"
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path)
    except ImportError:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "research-commons-raw")


def ensure_bucket(s3_client, bucket_name: str) -> None:
    """Create the target MinIO bucket if it does not already exist."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"404", "NoSuchBucket", "NotFound"}:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Created bucket '{bucket_name}'.")
        else:
            raise


def main() -> None:
    if not RAW_PAPERS_PATH.exists():
        raise FileNotFoundError(
            f"{RAW_PAPERS_PATH} not found. Run backend/fetch_papers.py first."
        )

    s3_client = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")
    ensure_bucket(s3_client, MINIO_BUCKET)

    object_key = "papers_raw.json"
    s3_client.upload_file(
        str(RAW_PAPERS_PATH),
        MINIO_BUCKET,
        object_key,
        ExtraArgs={"ContentType": "application/json"},
    )

    size_mb = RAW_PAPERS_PATH.stat().st_size / (1024 * 1024)
    print(f"Uploaded {RAW_PAPERS_PATH.name} ({size_mb:.2f} MB) -> s3://{MINIO_BUCKET}/{object_key}")


if __name__ == "__main__":
    main()
