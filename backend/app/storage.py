"""Private S3 access. Browsers never receive bucket credentials or public URLs."""

import time
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, Request

from app.core.config import Settings, get_settings


class ObjectStore:
    def __init__(self, settings: Settings):
        if not settings.s3_access_key or not settings.s3_secret_key:
            raise HTTPException(503, "Video storage is not configured. Contact the operator.")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=5,
                read_timeout=60,
                retries={"max_attempts": 2},
            ),
        )

    def put(self, key: str, file: BinaryIO, size: int, mime: str):
        file.seek(0)
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=file, ContentLength=size, ContentType=mime
        )

    def delete(self, key: str):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get(self, key: str, byte_range: str | None):
        args = {"Bucket": self.bucket, "Key": key}
        if byte_range:
            args["Range"] = byte_range
        return self.client.get_object(**args)


def get_store(request: Request) -> ObjectStore:
    return ObjectStore(request.app.state.settings)


def initialize():
    store = ObjectStore(get_settings())
    for attempt in range(30):
        try:
            try:
                store.client.head_bucket(Bucket=store.bucket)
            except ClientError as exc:
                if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                    raise
                store.client.create_bucket(Bucket=store.bucket)
            print("Private video bucket is ready.")
            return
        except (BotoCoreError, ClientError):
            if attempt == 29:
                raise RuntimeError("Object storage initialization failed") from None
            time.sleep(2)


if __name__ == "__main__":
    initialize()
