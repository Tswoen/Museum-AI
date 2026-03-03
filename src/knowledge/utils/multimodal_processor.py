import asyncio
import json
import os
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union
from datetime import datetime

from src.utils import logger
from src.utils.datetime_utils import utc_isoformat
from src.knowledge.utils.file_validator import (
    ProcessingStrategy,
    IMAGE_FILE_TYPES,
    VIDEO_FILE_TYPES,
    AUDIO_FILE_TYPES,
    FileTypeInfo,
)


@dataclass
class MediaMetadata:
    """多媒体元数据"""
    file_id: str
    filename: str
    file_path: str
    file_type: str
    category: str
    mime_type: str
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    context_text: Optional[str] = None
    custom_metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=utc_isoformat)


@dataclass
class AssociatedText:
    """关联文本配置"""
    media_id: str
    text_content: str
    text_type: str
    language: str = "zh"
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class MultimodalProcessor:
    """多模态文件处理器"""

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.media_dir = os.path.join(work_dir, "media")
        self.metadata_dir = os.path.join(work_dir, "media_metadata")
        os.makedirs(self.media_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)

    async def process_media_file(
        self,
        file_path: str | Path,
        params: Optional[dict] = None,
        associated_text: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """
        处理多媒体文件
        
        Args:
            file_path: 文件路径
            params: 处理参数
            associated_text: 关联的描述性文本
            tags: 标签列表
            
        Returns:
            处理结果
        """
        file_path = Path(file_path)
        params = params or {}
        
        ext = file_path.suffix.lower()
        type_info = IMAGE_FILE_TYPES.get(ext) or VIDEO_FILE_TYPES.get(ext) or AUDIO_FILE_TYPES.get(ext)
        
        if not type_info:
            raise ValueError(f"Unsupported media file type: {ext}")
        
        category = type_info.category
        
        processor_map = {
            "image": self._process_image,
            "video": self._process_video,
            "audio": self._process_audio,
        }
        
        processor = processor_map.get(category)
        if not processor:
            raise ValueError(f"No processor for category: {category}")
        
        return await processor(file_path, params, associated_text, tags)

    async def process_batch_from_json(
        self,
        items: list[dict],
        params: Optional[dict] = None,
    ) -> list[dict]:
        """
        从JSON数据批量处理多模态文件
        
        Args:
            items: JSON数据列表，每项包含url和description
            params: 处理参数
            
        Returns:
            处理结果列表
        """
        results = []
        
        for item in items:
            url = item.get("url", "")
            description = item.get("description", "")
            
            try:
                result = await self._process_from_url(url, description, params)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process URL {url}: {e}")
                results.append({
                    "status": "failed",
                    "error": str(e),
                    "url": url,
                })
        
        return results

    async def _process_from_url(
        self,
        url: str,
        description: str,
        params: Optional[dict] = None,
    ) -> dict:
        """
        从URL处理多模态文件
        
        Args:
            url: 文件URL
            description: 描述信息
            params: 处理参数
            
        Returns:
            处理结果
        """
        import tempfile
        import aiohttp
        
        params = params or {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download file: HTTP {response.status}")
                    
                    content_type = response.headers.get('Content-Type', '')
                    content = await response.read()
            
            ext = self._get_ext_from_content_type(content_type) or self._get_ext_from_url(url)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            type_info = IMAGE_FILE_TYPES.get(ext) or VIDEO_FILE_TYPES.get(ext) or AUDIO_FILE_TYPES.get(ext)
            
            if not type_info:
                os.unlink(tmp_path)
                raise ValueError(f"Unsupported media file type: {ext}")
            
            category = type_info.category
            
            processor_map = {
                "image": self._process_image,
                "video": self._process_video,
                "audio": self._process_audio,
            }
            
            processor = processor_map.get(category)
            if not processor:
                os.unlink(tmp_path)
                raise ValueError(f"No processor for category: {category}")
            
            result = await processor(Path(tmp_path), params, description, [])
            
            result["source_url"] = url
            result["is_from_url"] = True
            
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            raise

    async def _process_image(
        self,
        file_path: Path,
        params: dict,
        associated_text: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """处理图片文件"""
        try:
            from src.knowledge.utils.image_embedding_utils import (
                get_image_embedding,
                get_image_description,
                get_text_embedding,
            )
            
            image_embedding = await asyncio.to_thread(get_image_embedding, str(file_path))
            
            description = associated_text
            if not description:
                description = await asyncio.to_thread(get_image_description, str(file_path))
            
            text_embedding = None
            if description:
                text_embedding = await asyncio.to_thread(get_text_embedding, description)
            
            media_id = self._generate_media_id(file_path)
            
            metadata = MediaMetadata(
                file_id=media_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_type=file_path.suffix.lower(),
                category="image",
                mime_type=IMAGE_FILE_TYPES[file_path.suffix.lower()].mime_type,
                description=description,
                tags=tags or [],
                context_text=associated_text,
            )
            
            await self._save_media_metadata(metadata)
            
            return {
                "status": "success",
                "media_id": media_id,
                "category": "image",
                "embeddings": {
                    "image": image_embedding.tolist() if hasattr(image_embedding, 'tolist') else image_embedding,
                    "text": text_embedding.tolist() if text_embedding is not None and hasattr(text_embedding, 'tolist') else text_embedding,
                },
                "description": description,
                "metadata": metadata.__dict__,
            }
            
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}, {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": str(e),
                "file_path": str(file_path),
            }

    async def _process_video(
        self,
        file_path: Path,
        params: dict,
        associated_text: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """处理视频文件"""
        try:
            video_info = await self._extract_video_info(file_path)
            
            frames = await self._extract_video_frames(file_path, params)
            
            frame_embeddings = []
            if frames:
                from src.knowledge.utils.image_embedding_utils import get_image_embedding
                
                for frame_path in frames:
                    try:
                        embedding = await asyncio.to_thread(get_image_embedding, frame_path)
                        frame_embeddings.append(embedding.tolist() if hasattr(embedding, 'tolist') else embedding)
                    except Exception as e:
                        logger.warning(f"Failed to embed frame {frame_path}: {e}")
            
            description = associated_text or f"视频文件: {file_path.name}"
            if video_info.get("duration"):
                description += f", 时长: {video_info['duration']:.2f}秒"
            
            media_id = self._generate_media_id(file_path)
            
            metadata = MediaMetadata(
                file_id=media_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_type=file_path.suffix.lower(),
                category="video",
                mime_type=VIDEO_FILE_TYPES[file_path.suffix.lower()].mime_type,
                description=description,
                tags=tags or [],
                context_text=associated_text,
                custom_metadata={
                    "duration": video_info.get("duration"),
                    "fps": video_info.get("fps"),
                    "resolution": video_info.get("resolution"),
                    "frame_count": len(frames),
                },
            )
            
            await self._save_media_metadata(metadata)
            
            return {
                "status": "success",
                "media_id": media_id,
                "category": "video",
                "embeddings": {
                    "frames": frame_embeddings,
                },
                "description": description,
                "metadata": metadata.__dict__,
                "frame_count": len(frames),
            }
            
        except Exception as e:
            logger.error(f"Failed to process video {file_path}: {e}, {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": str(e),
                "file_path": str(file_path),
            }

    async def _process_audio(
        self,
        file_path: Path,
        params: dict,
        associated_text: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """处理音频文件"""
        try:
            audio_info = await self._extract_audio_info(file_path)
            
            description = associated_text or f"音频文件: {file_path.name}"
            if audio_info.get("duration"):
                description += f", 时长: {audio_info['duration']:.2f}秒"
            
            media_id = self._generate_media_id(file_path)
            
            metadata = MediaMetadata(
                file_id=media_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_type=file_path.suffix.lower(),
                category="audio",
                mime_type=AUDIO_FILE_TYPES[file_path.suffix.lower()].mime_type,
                description=description,
                tags=tags or [],
                context_text=associated_text,
                custom_metadata={
                    "duration": audio_info.get("duration"),
                    "sample_rate": audio_info.get("sample_rate"),
                    "channels": audio_info.get("channels"),
                },
            )
            
            await self._save_media_metadata(metadata)
            
            return {
                "status": "success",
                "media_id": media_id,
                "category": "audio",
                "embeddings": {},
                "description": description,
                "metadata": metadata.__dict__,
            }
            
        except Exception as e:
            logger.error(f"Failed to process audio {file_path}: {e}, {traceback.format_exc()}")
            return {
                "status": "failed",
                "error": str(e),
                "file_path": str(file_path),
            }

    async def _extract_video_info(self, file_path: Path) -> dict:
        """提取视频信息"""
        try:
            import subprocess
            
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                video_stream = None
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        video_stream = stream
                        break
                
                format_info = data.get("format", {})
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0,
                    "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}" if video_stream else None,
                }
        except Exception as e:
            logger.warning(f"Failed to extract video info: {e}")
        
        return {}

    async def _extract_audio_info(self, file_path: Path) -> dict:
        """提取音频信息"""
        try:
            import subprocess
            
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                audio_stream = None
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "audio":
                        audio_stream = stream
                        break
                
                format_info = data.get("format", {})
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
                    "channels": int(audio_stream.get("channels", 0)) if audio_stream else 0,
                }
        except Exception as e:
            logger.warning(f"Failed to extract audio info: {e}")
        
        return {}

    async def _extract_video_frames(
        self,
        file_path: Path,
        params: dict,
        max_frames: int = 10,
        interval: float = 1.0,
    ) -> list[str]:
        """从视频中提取帧"""
        frames = []
        
        try:
            import subprocess
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_pattern = os.path.join(temp_dir, "frame_%04d.jpg")
                
                duration = await self._get_video_duration(file_path)
                if duration > 0:
                    actual_interval = max(interval, duration / max_frames)
                else:
                    actual_interval = interval
                
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-i", str(file_path),
                        "-vf", f"fps=1/{actual_interval}",
                        "-frames:v", str(max_frames),
                        "-q:v", "2",
                        output_pattern
                    ],
                    capture_output=True,
                    timeout=60
                )
                
                for filename in sorted(os.listdir(temp_dir)):
                    if filename.startswith("frame_") and filename.endswith(".jpg"):
                        frames.append(os.path.join(temp_dir, filename))
                        
        except Exception as e:
            logger.warning(f"Failed to extract video frames: {e}")
        
        return frames

    async def _get_video_duration(self, file_path: Path) -> float:
        """获取视频时长"""
        info = await self._extract_video_info(file_path)
        return info.get("duration", 0)

    def _generate_media_id(self, file_path: Path) -> str:
        """生成媒体ID"""
        from src.utils import hashstr
        import time
        
        return f"media_{hashstr(str(file_path) + str(time.time()), 8)}"

    def _get_ext_from_content_type(self, content_type: str) -> Optional[str]:
        """从Content-Type获取文件扩展名"""
        if not content_type:
            return None
        
        content_type = content_type.lower().split(';')[0].strip()
        
        type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/webp': '.webp',
            'image/tiff': '.tiff',
            'image/svg+xml': '.svg',
            'video/mp4': '.mp4',
            'video/x-msvideo': '.avi',
            'video/quicktime': '.mov',
            'video/x-ms-wmv': '.wmv',
            'video/x-flv': '.flv',
            'video/x-matroska': '.mkv',
            'video/webm': '.webm',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'audio/flac': '.flac',
            'audio/aac': '.aac',
            'audio/mp4': '.m4a',
        }
        
        return type_map.get(content_type)

    def _get_ext_from_url(self, url: str) -> str:
        """从URL获取文件扩展名"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        for ext in IMAGE_FILE_TYPES.keys():
            if path.endswith(ext):
                return ext
        
        for ext in VIDEO_FILE_TYPES.keys():
            if path.endswith(ext):
                return ext
        
        for ext in AUDIO_FILE_TYPES.keys():
            if path.endswith(ext):
                return ext
        
        return '.bin'

    async def _save_media_metadata(self, metadata: MediaMetadata) -> None:
        """保存媒体元数据"""
        metadata_path = os.path.join(self.metadata_dir, f"{metadata.file_id}.json")
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata.__dict__, f, ensure_ascii=False, indent=2)

    async def load_media_metadata(self, media_id: str) -> Optional[MediaMetadata]:
        """加载媒体元数据"""
        metadata_path = os.path.join(self.metadata_dir, f"{media_id}.json")
        
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return MediaMetadata(**data)
        except Exception as e:
            logger.error(f"Failed to load media metadata {media_id}: {e}")
            return None

    async def update_associated_text(
        self,
        media_id: str,
        text_content: str,
        text_type: str = "description",
        tags: Optional[list[str]] = None,
    ) -> bool:
        """
        更新媒体文件的关联文本
        
        Args:
            media_id: 媒体ID
            text_content: 文本内容
            text_type: 文本类型（description, context, annotation等）
            tags: 标签列表
            
        Returns:
            是否更新成功
        """
        metadata = await self.load_media_metadata(media_id)
        if not metadata:
            return False
        
        if text_type == "description":
            metadata.description = text_content
        elif text_type == "context":
            metadata.context_text = text_content
        else:
            metadata.custom_metadata[text_type] = text_content
        
        if tags:
            metadata.tags = list(set(metadata.tags + tags))
        
        await self._save_media_metadata(metadata)
        return True

    async def batch_process_media(
        self,
        file_paths: list[str | Path],
        params: Optional[dict] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[dict]:
        """
        批量处理媒体文件
        
        Args:
            file_paths: 文件路径列表
            params: 处理参数
            progress_callback: 进度回调函数
            
        Returns:
            处理结果列表
        """
        results = []
        total = len(file_paths)
        
        for idx, file_path in enumerate(file_paths):
            result = await self.process_media_file(file_path, params)
            results.append(result)
            
            if progress_callback:
                await progress_callback(idx + 1, total, result)
        
        return results


class AssociatedTextManager:
    """关联文本管理器"""

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.associations_dir = os.path.join(work_dir, "text_associations")
        os.makedirs(self.associations_dir, exist_ok=True)

    async def create_association(
        self,
        media_id: str,
        text_content: str,
        text_type: str = "description",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> AssociatedText:
        """创建关联文本"""
        from src.utils import hashstr
        import time
        
        association_id = f"assoc_{hashstr(media_id + str(time.time()), 6)}"
        
        association = AssociatedText(
            media_id=media_id,
            text_content=text_content,
            text_type=text_type,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        association_path = os.path.join(self.associations_dir, f"{association_id}.json")
        with open(association_path, 'w', encoding='utf-8') as f:
            json.dump(association.__dict__, f, ensure_ascii=False, indent=2)
        
        return association

    async def get_associations_for_media(self, media_id: str) -> list[AssociatedText]:
        """获取媒体文件的所有关联文本"""
        associations = []
        
        for filename in os.listdir(self.associations_dir):
            if not filename.endswith('.json'):
                continue
            
            try:
                with open(os.path.join(self.associations_dir, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("media_id") == media_id:
                        associations.append(AssociatedText(**data))
            except Exception as e:
                logger.warning(f"Failed to load association {filename}: {e}")
        
        return associations

    async def delete_association(self, association_id: str) -> bool:
        """删除关联文本"""
        association_path = os.path.join(self.associations_dir, f"{association_id}.json")
        
        if os.path.exists(association_path):
            os.remove(association_path)
            return True
        
        return False
