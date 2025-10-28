"""通用工具函数"""

import logging
import base64
import uuid
from pathlib import Path
from fastapi import Request
from sqlalchemy.orm import Session

from src.storage.db.models import OperationLog, User

from src.utils.logging_config import logger


def setup_logging():
    """配置应用程序日志格式"""
    # 配置日志格式
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S", force=True
    )

    # 确保uvicorn的日志也使用相同格式
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")

    # 创建格式化器
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s", datefmt="%m-%d %H:%M:%S")

    # 为所有处理器设置格式化器
    for handler in uvicorn_logger.handlers:
        handler.setFormatter(formatter)
    for handler in uvicorn_access_logger.handlers:
        handler.setFormatter(formatter)


def log_operation(db: Session, user_id: int, operation: str, details: str = None, request: Request = None):
    """记录用户操作日志"""
    ip_address = None
    if request:
        ip_address = request.client.host if request.client else None

    log = OperationLog(user_id=user_id, operation=operation, details=details, ip_address=ip_address)
    db.add(log)
    db.commit()


def get_user_dict(user: User, include_password: bool = False) -> dict:
    """获取用户字典表示"""
    return user.to_dict(include_password)


def convert_serializable(obj):
    """将对象转换为可序列化的格式"""
    if isinstance(obj, list | tuple):
        return [convert_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: convert_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return convert_serializable(vars(obj))
    return obj

def save_chat_images(images: list, thread_id: str) -> list:
    """
    保存聊天图片到服务器本地目录
    
    Args:
        images: 图片数据列表，可以是base64编码的字符串或图片URL
        thread_id: 对话线程ID，用于创建目录结构
        
    Returns:
        list: 保存后的图片路径列表
    """
    saved_paths = []
    
    # 创建图片保存目录
    images_dir = Path("saves/chat_images")
    thread_dir = images_dir / thread_id
    thread_dir.mkdir(parents=True, exist_ok=True)
    
    for i, image_data in enumerate(images):
        try:
            
            # 生成唯一的文件名
            filename = f"image_{uuid.uuid4().hex[:8]}_{i}.png"
            file_path = thread_dir / filename
            
            # 处理不同类型的图片数据
            if isinstance(image_data, str):
                if image_data.startswith('data:image'):
                    # 处理base64编码的图片数据
                    # 格式: data:image/png;base64,<base64_data>
                    if ';base64,' in image_data:
                        header, base64_str = image_data.split(';base64,', 1)
                        image_bytes = base64.b64decode(base64_str)
                        
                        # 保存图片文件
                        with open(file_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        saved_paths.append(str(file_path))
                        logger.info(f"保存base64图片到: {file_path}")
                    else:
                        logger.warning(f"无法解析的base64图片格式: {image_data[:100]}...")
                elif image_data.startswith(('http://', 'https://')):
                    # 处理URL图片，直接保存URL
                    saved_paths.append(image_data)
                    logger.info(f"保留图片URL: {image_data}")
                else:
                    # 可能是文件路径或其他格式，直接保存
                    saved_paths.append(image_data)
                    logger.info(f"保留图片数据: {image_data[:100]}...")
            else:
                logger.warning(f"无法处理的图片数据类型: {type(image_data)}")
                
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            # 即使保存失败，也保留原始数据
            saved_paths.append(image_data)
    
    return saved_paths