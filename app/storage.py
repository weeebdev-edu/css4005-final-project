"""Object storage for attachments: local directory, Amazon S3 or Google Cloud Storage.

Credentials are never read here: boto3 and google-cloud-storage use their
default chains (instance role / service account / env), which is what the
project requires. boto3 also honours AWS_ENDPOINT_URL (moto, MinIO...).
"""

from pathlib import Path


class LocalStorage:
    def __init__(self, directory: str):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def check(self) -> bool:
        return self.root.is_dir()


class S3Storage:
    def __init__(self, bucket: str):
        import boto3

        self.bucket = bucket
        self.client = boto3.client("s3")

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def check(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


class GCSStorage:
    def __init__(self, bucket: str):
        from google.cloud import storage

        self.bucket = storage.Client().bucket(bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.bucket.blob(key).upload_from_string(data, content_type=content_type)

    def get(self, key: str) -> bytes:
        return self.bucket.blob(key).download_as_bytes()

    def check(self) -> bool:
        try:
            return self.bucket.exists()
        except Exception:
            return False


def make_storage(backend: str, bucket: str):
    return {"local": LocalStorage, "s3": S3Storage, "gcs": GCSStorage}[backend](bucket)
