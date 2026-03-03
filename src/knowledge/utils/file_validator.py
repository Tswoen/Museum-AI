import hashlib
import imghdr
import os
import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils import logger


class FileValidationError(Exception):
    """文件校验错误基类"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class FileTooLargeError(FileValidationError):
    """文件过大错误"""
    def __init__(self, file_size: int, max_size: int):
        self.file_size = file_size
        self.max_size = max_size
        message = f"文件大小 {self._format_size(file_size)} 超过最大限制 {self._format_size(max_size)}"
        super().__init__(message, "FILE_TOO_LARGE")

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


class UnsupportedFileTypeError(FileValidationError):
    """不支持的文件类型错误"""
    def __init__(self, file_ext: str, supported_types: list[str]):
        self.file_ext = file_ext
        self.supported_types = supported_types
        message = f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(supported_types)}"
        super().__init__(message, "UNSUPPORTED_FILE_TYPE")


class FileCorruptedError(FileValidationError):
    """文件损坏错误"""
    def __init__(self, message: str = "文件损坏或不完整"):
        super().__init__(message, "FILE_CORRUPTED")


class FileSecurityError(FileValidationError):
    """文件安全错误"""
    def __init__(self, message: str = "检测到潜在的安全风险"):
        super().__init__(message, "FILE_SECURITY_RISK")


class ProcessingStrategy(Enum):
    """处理策略枚举"""
    TEXT = "text"
    MULTIMODAL = "multimodal"


@dataclass
class FileTypeInfo:
    """文件类型信息"""
    category: str
    strategy: ProcessingStrategy
    mime_type: str
    description: str


TEXT_FILE_TYPES = {
    ".txt": FileTypeInfo("text", ProcessingStrategy.TEXT, "text/plain", "纯文本文件"),
    ".md": FileTypeInfo("text", ProcessingStrategy.TEXT, "text/markdown", "Markdown文档"),
    ".doc": FileTypeInfo("text", ProcessingStrategy.TEXT, "application/msword", "Word文档"),
    ".docx": FileTypeInfo("text", ProcessingStrategy.TEXT, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Word文档"),
    ".pdf": FileTypeInfo("text", ProcessingStrategy.TEXT, "application/pdf", "PDF文档"),
    ".html": FileTypeInfo("text", ProcessingStrategy.TEXT, "text/html", "HTML文档"),
    ".htm": FileTypeInfo("text", ProcessingStrategy.TEXT, "text/html", "HTML文档"),
    ".json": FileTypeInfo("text", ProcessingStrategy.TEXT, "application/json", "JSON文件"),
    ".csv": FileTypeInfo("text", ProcessingStrategy.TEXT, "text/csv", "CSV表格"),
    ".xls": FileTypeInfo("text", ProcessingStrategy.TEXT, "application/vnd.ms-excel", "Excel表格"),
    ".xlsx": FileTypeInfo("text", ProcessingStrategy.TEXT, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Excel表格"),
}

IMAGE_FILE_TYPES = {
    ".jpg": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/jpeg", "JPEG图片"),
    ".jpeg": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/jpeg", "JPEG图片"),
    ".png": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/png", "PNG图片"),
    ".gif": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/gif", "GIF动图"),
    ".bmp": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/bmp", "BMP图片"),
    ".webp": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/webp", "WebP图片"),
    ".tiff": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/tiff", "TIFF图片"),
    ".tif": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/tiff", "TIFF图片"),
    ".svg": FileTypeInfo("image", ProcessingStrategy.MULTIMODAL, "image/svg+xml", "SVG矢量图"),
}

VIDEO_FILE_TYPES = {
    ".mp4": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/mp4", "MP4视频"),
    ".avi": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/x-msvideo", "AVI视频"),
    ".mov": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/quicktime", "MOV视频"),
    ".wmv": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/x-ms-wmv", "WMV视频"),
    ".flv": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/x-flv", "FLV视频"),
    ".mkv": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/x-matroska", "MKV视频"),
    ".webm": FileTypeInfo("video", ProcessingStrategy.MULTIMODAL, "video/webm", "WebM视频"),
}

AUDIO_FILE_TYPES = {
    ".mp3": FileTypeInfo("audio", ProcessingStrategy.MULTIMODAL, "audio/mpeg", "MP3音频"),
    ".wav": FileTypeInfo("audio", ProcessingStrategy.MULTIMODAL, "audio/wav", "WAV音频"),
    ".ogg": FileTypeInfo("audio", ProcessingStrategy.MULTIMODAL, "audio/ogg", "OGG音频"),
    ".flac": FileTypeInfo("audio", ProcessingStrategy.MULTIMODAL, "audio/flac", "FLAC音频"),
    ".aac": FileTypeInfo("audio", ProcessingStrategy.MULTIMODAL, "audio/aac", "AAC音频"),
    ".m4a": FileTypeInfo("audio", ProcessingStrategy.MULTIMODAL, "audio/mp4", "M4A音频"),
}

ALL_SUPPORTED_TYPES = {}
ALL_SUPPORTED_TYPES.update(TEXT_FILE_TYPES)
ALL_SUPPORTED_TYPES.update(IMAGE_FILE_TYPES)
ALL_SUPPORTED_TYPES.update(VIDEO_FILE_TYPES)
ALL_SUPPORTED_TYPES.update(AUDIO_FILE_TYPES)

DEFAULT_SIZE_LIMITS = {
    "text": 100 * 1024 * 1024,
    "image": 50 * 1024 * 1024,
    "video": 500 * 1024 * 1024,
    "audio": 100 * 1024 * 1024,
    "default": 100 * 1024 * 1024,
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".com", ".pif", ".scr", ".vbs", ".js", ".jar",
    ".msi", ".sh", ".bash", ".zsh", ".app", ".deb", ".rpm", ".dmg", ".pkg",
    ".run", ".bin", ".script", ".command", ".ps1", ".ps2", ".psm1", ".psd1",
}

MAGIC_NUMBERS = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'BM': 'bmp',
    b'RIFF': 'webp',
    b'\x00\x00\x01\x00': 'ico',
    b'%PDF': 'pdf',
    b'PK\x03\x04': 'zip',
    b'\x50\x4B\x03\x04': 'zip',
}


class FileValidator:
    """文件校验器"""

    def __init__(
        self,
        size_limits: Optional[dict[str, int]] = None,
        allowed_types: Optional[set[str]] = None,
        enable_security_check: bool = True,
        enable_integrity_check: bool = True,
    ):
        self.size_limits = size_limits or DEFAULT_SIZE_LIMITS.copy()
        self.allowed_types = allowed_types or set(ALL_SUPPORTED_TYPES.keys())
        self.enable_security_check = enable_security_check
        self.enable_integrity_check = enable_integrity_check

    def validate_file(self, file_path: str | Path) -> Tuple[bool, Optional[FileValidationError], Optional[FileTypeInfo]]:
        """
        全面校验文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Tuple[是否有效, 错误信息, 文件类型信息]
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False, FileValidationError(f"文件不存在: {file_path}", "FILE_NOT_FOUND"), None
        
        if not file_path.is_file():
            return False, FileValidationError(f"路径不是文件: {file_path}", "NOT_A_FILE"), None

        is_valid, error, type_info = self.validate_file_extension(file_path)
        if not is_valid:
            return False, error, None

        is_valid, error = self.validate_file_size(file_path, type_info)
        if not is_valid:
            return False, error, None

        if self.enable_security_check:
            is_valid, error = self.security_check(file_path)
            if not is_valid:
                return False, error, None

        if self.enable_integrity_check:
            is_valid, error = self.integrity_check(file_path, type_info)
            if not is_valid:
                return False, error, None

        return True, None, type_info

    def validate_file_extension(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError], Optional[FileTypeInfo]]:
        """校验文件扩展名"""
        ext = file_path.suffix.lower()
        
        if ext in DANGEROUS_EXTENSIONS:
            return False, FileSecurityError(f"禁止上传可执行文件: {ext}"), None
        
        if ext not in self.allowed_types:
            supported = sorted(self.allowed_types)
            return False, UnsupportedFileTypeError(ext, supported), None
        
        type_info = ALL_SUPPORTED_TYPES.get(ext)
        return True, None, type_info

    def validate_file_size(self, file_path: Path, type_info: Optional[FileTypeInfo] = None) -> Tuple[bool, Optional[FileValidationError]]:
        """校验文件大小"""
        try:
            file_size = file_path.stat().st_size
        except OSError as e:
            return False, FileValidationError(f"无法获取文件大小: {e}", "CANNOT_GET_SIZE")
        
        category = type_info.category if type_info else "default"
        max_size = self.size_limits.get(category, self.size_limits.get("default", 100 * 1024 * 1024))
        
        if file_size > max_size:
            return False, FileTooLargeError(file_size, max_size)
        
        if file_size == 0:
            return False, FileCorruptedError("文件大小为0，可能为空文件或损坏")
        
        return True, None

    def security_check(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError]]:
        """安全检查"""
        ext = file_path.suffix.lower()
        
        if ext in DANGEROUS_EXTENSIONS:
            return False, FileSecurityError(f"检测到危险文件类型: {ext}")
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)
            
            suspicious_patterns = [
                b'<script',
                b'javascript:',
                b'data:text/html',
                b'vbscript:',
                b'onload=',
                b'onerror=',
            ]
            
            header_lower = header.lower()
            for pattern in suspicious_patterns:
                if pattern in header_lower:
                    return False, FileSecurityError(f"检测到可疑内容模式")
                    
        except Exception as e:
            logger.warning(f"安全检查读取文件失败: {e}")
        
        return True, None

    def integrity_check(self, file_path: Path, type_info: Optional[FileTypeInfo] = None) -> Tuple[bool, Optional[FileValidationError]]:
        """完整性检查"""
        if not type_info:
            return True, None
        
        category = type_info.category
        
        if category == "image":
            return self._check_image_integrity(file_path)
        elif category == "text":
            return self._check_text_integrity(file_path)
        elif category == "video":
            return self._check_video_integrity(file_path)
        
        return True, None

    def _check_image_integrity(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError]]:
        """检查图片完整性"""
        try:
            img_type = self._detect_image_type(file_path)
            if img_type is None:
                actual_ext = file_path.suffix.lower()
                expected_type = actual_ext.lstrip('.')
                if expected_type in ['jpg', 'jpeg']:
                    expected_type = 'jpeg'
                elif expected_type == 'tif':
                    expected_type = 'tiff'
                
                if expected_type not in ['svg', 'webp']:
                    return False, FileCorruptedError(f"图片文件可能已损坏或格式不正确")
            
            from PIL import Image
            with Image.open(file_path) as img:
                img.verify()
            
            return True, None
            
        except ImportError:
            logger.warning("PIL库未安装，跳过图片完整性深度检查")
            return True, None
        except Exception as e:
            return False, FileCorruptedError(f"图片文件损坏: {str(e)}")

    def _check_text_integrity(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError]]:
        """检查文本文件完整性"""
        try:
            ext = file_path.suffix.lower()
            
            if ext == '.pdf':
                return self._check_pdf_integrity(file_path)
            elif ext in ['.docx', '.xlsx', '.pptx']:
                return self._check_office_integrity(file_path)
            elif ext in ['.doc', '.xls', '.ppt']:
                return True, None
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read(1024)
                return True, None
                
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    f.read(1024)
                return True, None
            except Exception:
                return False, FileCorruptedError("文本文件编码无法识别")
        except Exception as e:
            return False, FileCorruptedError(f"文本文件损坏: {str(e)}")

    def _check_pdf_integrity(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError]]:
        """检查PDF文件完整性"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    return False, FileCorruptedError("PDF文件头无效")
            return True, None
        except Exception as e:
            return False, FileCorruptedError(f"PDF文件损坏: {str(e)}")

    def _check_office_integrity(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError]]:
        """检查Office文件完整性"""
        try:
            import zipfile
            with zipfile.ZipFile(file_path, 'r') as zf:
                if zf.testzip() is not None:
                    return False, FileCorruptedError("Office文件内部结构损坏")
            return True, None
        except zipfile.BadZipFile:
            return False, FileCorruptedError("Office文件格式无效")
        except Exception as e:
            return False, FileCorruptedError(f"Office文件损坏: {str(e)}")

    def _check_video_integrity(self, file_path: Path) -> Tuple[bool, Optional[FileValidationError]]:
        """检查视频文件完整性"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
            
            ext = file_path.suffix.lower()
            video_signatures = {
                '.mp4': [b'ftyp', b'mp4', b'isom', b'M4V'],
                '.avi': [b'AVI'],
                '.mkv': [b'\x1aE\xdf\xa3'],
                '.webm': [b'\x1aE\xdf\xa3'],
                '.flv': [b'FLV'],
                '.mov': [b'moov', b'ftyp'],
            }
            
            if ext in video_signatures:
                signatures = video_signatures[ext]
                found = any(sig in header for sig in signatures)
                if not found:
                    return False, FileCorruptedError(f"视频文件格式不正确或损坏")
            
            return True, None
            
        except Exception as e:
            return False, FileCorruptedError(f"视频文件检查失败: {str(e)}")

    def _detect_image_type(self, file_path: Path) -> Optional[str]:
        """检测图片实际类型"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
            
            for magic, img_type in MAGIC_NUMBERS.items():
                if header.startswith(magic):
                    return img_type
            
            return imghdr.what(file_path)
            
        except Exception:
            return None

    @staticmethod
    def calculate_checksum(file_path: Path, algorithm: str = "sha256") -> str:
        """计算文件校验和"""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()

    @staticmethod
    def get_file_category(file_path: Path) -> str:
        """获取文件类别"""
        ext = file_path.suffix.lower()
        
        if ext in TEXT_FILE_TYPES:
            return "text"
        elif ext in IMAGE_FILE_TYPES:
            return "image"
        elif ext in VIDEO_FILE_TYPES:
            return "video"
        elif ext in AUDIO_FILE_TYPES:
            return "audio"
        else:
            return "unknown"

    @staticmethod
    def get_processing_strategy(file_path: Path) -> ProcessingStrategy:
        """获取处理策略"""
        ext = file_path.suffix.lower()
        type_info = ALL_SUPPORTED_TYPES.get(ext)
        
        if type_info:
            return type_info.strategy
        
        return ProcessingStrategy.TEXT


def validate_upload_file(
    file_path: str | Path,
    size_limits: Optional[dict[str, int]] = None,
    allowed_types: Optional[set[str]] = None,
) -> Tuple[bool, Optional[FileValidationError], Optional[FileTypeInfo]]:
    """
    便捷函数：校验上传的文件
    
    Args:
        file_path: 文件路径
        size_limits: 大小限制配置
        allowed_types: 允许的文件类型
        
    Returns:
        Tuple[是否有效, 错误信息, 文件类型信息]
    """
    validator = FileValidator(size_limits=size_limits, allowed_types=allowed_types)
    return validator.validate_file(file_path)


def get_all_supported_extensions() -> list[str]:
    """获取所有支持的文件扩展名"""
    return sorted(ALL_SUPPORTED_TYPES.keys())


def get_file_types_by_category() -> dict[str, list[str]]:
    """按类别获取支持的文件类型"""
    return {
        "text": sorted(TEXT_FILE_TYPES.keys()),
        "image": sorted(IMAGE_FILE_TYPES.keys()),
        "video": sorted(VIDEO_FILE_TYPES.keys()),
        "audio": sorted(AUDIO_FILE_TYPES.keys()),
    }
