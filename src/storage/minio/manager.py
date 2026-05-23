import os
import posixpath
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config import config

from .client import MinIOClient, UploadResult, get_minio_client


@dataclass
class StoredObject:
    url: str
    bucket_name: str
    object_name: str
    content_type: str
    size: int

    @classmethod
    def from_upload_result(cls, result: UploadResult, content_type: str, size: int) -> "StoredObject":
        return cls(
            url=result.url,
            bucket_name=result.bucket_name,
            object_name=result.object_name,
            content_type=content_type,
            size=size,
        )

    def to_dict(self) -> dict:
        return asdict(self)


class MinIOStorageManager:
    """Business-level storage helpers for uploaded files and parsing artifacts."""

    def __init__(self, client: MinIOClient | None = None):
        self.client = client or get_minio_client()
        self.raw_files_bucket = config.minio_bucket_raw_files or "raw-files"
        self.parsed_files_bucket = config.minio_bucket_parsed_files or "parsed-files"
        self.generated_images_bucket = config.minio_bucket_generated_images or "generated-images"

    def upload_raw_file(
        self,
        data: bytes,
        filename: str,
        content_type: str | None = None,
        prefix: str = "uploads",
    ) -> StoredObject:
        return self._upload_bytes(
            bucket_name=self.raw_files_bucket,
            data=data,
            filename=filename,
            content_type=content_type,
            prefix=prefix,
        )

    def upload_raw_file_from_path(
        self,
        file_path: str | os.PathLike,
        object_name: str | None = None,
        prefix: str = "uploads",
    ) -> StoredObject:
        path = Path(file_path)
        filename = object_name or path.name
        with path.open("rb") as file:
            data = file.read()
        return self.upload_raw_file(data=data, filename=filename, prefix=prefix)

    def upload_parsed_image(
        self,
        data: bytes,
        filename: str | None = None,
        file_extension: str = "png",
        content_type: str | None = None,
        prefix: str = "parsed/images",
    ) -> StoredObject:
        filename = filename or f"{uuid.uuid4().hex}.{file_extension.lstrip('.')}"
        content_type = content_type or self._image_content_type(file_extension)
        return self._upload_bytes(
            bucket_name=self.parsed_files_bucket,
            data=data,
            filename=filename,
            content_type=content_type,
            prefix=prefix,
        )

    def upload_parsed_file(
        self,
        data: bytes,
        filename: str,
        content_type: str | None = None,
        prefix: str = "parsed/files",
    ) -> StoredObject:
        return self._upload_bytes(
            bucket_name=self.parsed_files_bucket,
            data=data,
            filename=filename,
            content_type=content_type,
            prefix=prefix,
        )

    def upload_generated_image(
        self,
        data: bytes,
        filename: str | None = None,
        file_extension: str = "jpg",
        content_type: str | None = None,
        prefix: str = "generated/images",
    ) -> StoredObject:
        filename = filename or f"{uuid.uuid4().hex}.{file_extension.lstrip('.')}"
        content_type = content_type or self._image_content_type(file_extension)
        return self._upload_bytes(
            bucket_name=self.generated_images_bucket,
            data=data,
            filename=filename,
            content_type=content_type,
            prefix=prefix,
        )

    def _upload_bytes(
        self,
        bucket_name: str,
        data: bytes,
        filename: str,
        content_type: str | None,
        prefix: str,
    ) -> StoredObject:
        object_name = self._build_object_name(filename, prefix)
        content_type = content_type or self.client._guess_content_type(object_name)
        result = self.client.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            data=data,
            content_type=content_type,
        )
        return StoredObject.from_upload_result(result, content_type=content_type, size=len(data))

    def _build_object_name(self, filename: str, prefix: str) -> str:
        clean_name = Path(filename).name
        stem, suffix = os.path.splitext(clean_name)
        object_file = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
        clean_prefix = prefix.strip("/")
        if not clean_prefix:
            return object_file
        return posixpath.join(clean_prefix, object_file)

    def _image_content_type(self, file_extension: str) -> str:
        extension = file_extension.lower().lstrip(".")
        if extension == "jpg":
            extension = "jpeg"
        return f"image/{extension}"


_storage_manager: MinIOStorageManager | None = None


def get_minio_storage_manager() -> MinIOStorageManager:
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = MinIOStorageManager()
    return _storage_manager
