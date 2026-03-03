"""知识库工具模块

包含知识库相关的工具函数：
- kb_utils: 知识库通用工具函数
- indexing: 文件处理和索引相关功能
- file_validator: 文件校验工具
- multimodal_processor: 多模态文件处理器
"""

from .kb_utils import (
    calculate_content_hash,
    get_embedding_config,
    prepare_item_metadata,
    split_text_into_chunks,
    split_text_into_qa_chunks,
    validate_file_path,
)

from .file_validator import (
    FileValidator,
    FileValidationError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    FileCorruptedError,
    FileSecurityError,
    ProcessingStrategy,
    FileTypeInfo,
    validate_upload_file,
    get_all_supported_extensions,
    get_file_types_by_category,
    TEXT_FILE_TYPES,
    IMAGE_FILE_TYPES,
    VIDEO_FILE_TYPES,
    AUDIO_FILE_TYPES,
    ALL_SUPPORTED_TYPES,
)

from .multimodal_processor import (
    MultimodalProcessor,
    MediaMetadata,
    AssociatedText,
    AssociatedTextManager,
)

__all__ = [
    "calculate_content_hash",
    "get_embedding_config",
    "prepare_item_metadata",
    "split_text_into_chunks",
    "split_text_into_qa_chunks",
    "validate_file_path",
    "FileValidator",
    "FileValidationError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "FileCorruptedError",
    "FileSecurityError",
    "ProcessingStrategy",
    "FileTypeInfo",
    "validate_upload_file",
    "get_all_supported_extensions",
    "get_file_types_by_category",
    "TEXT_FILE_TYPES",
    "IMAGE_FILE_TYPES",
    "VIDEO_FILE_TYPES",
    "AUDIO_FILE_TYPES",
    "ALL_SUPPORTED_TYPES",
    "MultimodalProcessor",
    "MediaMetadata",
    "AssociatedText",
    "AssociatedTextManager",
]
