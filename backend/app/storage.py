"""File storage for claim documents.

Two backends with the same three methods (save, read, delete):

* ``S3Storage``    - Amazon S3, used in production.
* ``LocalStorage`` - a folder on disk, used in development and tests.

The rest of the app calls ``get_storage()`` and does not care which one it
gets. Files are not stored on the EC2 server's disk in production because
that disk is lost if the instance is replaced, and it is not shared if a
second instance is added behind a load balancer.
"""
import os

from flask import current_app


class LocalStorage:
    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)

    def _path(self, key):
        path = os.path.abspath(os.path.join(self.base_dir, key))
        # Refuse keys such as "../../etc/passwd" that escape the upload folder.
        if not path.startswith(self.base_dir + os.sep):
            raise ValueError("Invalid storage key.")
        return path

    def save(self, key, data, content_type):
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)

    def read(self, key):
        with open(self._path(key), "rb") as handle:
            return handle.read()

    def delete(self, key):
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass


class S3Storage:
    def __init__(self, bucket, region):
        import boto3  # imported here so local development does not need AWS set up

        self.bucket = bucket
        # No access keys in code: on EC2, boto3 gets temporary credentials
        # from the instance's IAM role automatically.
        self.client = boto3.client("s3", region_name=region)

    def save(self, key, data, content_type):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def read(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)


def get_storage():
    bucket = current_app.config.get("S3_BUCKET")
    if bucket:
        return S3Storage(bucket, current_app.config["AWS_REGION"])
    return LocalStorage(current_app.config["UPLOAD_DIR"])
