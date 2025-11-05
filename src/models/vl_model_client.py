import os
import base64
import requests
from typing import Optional, Dict, Any
from PIL import Image
from io import BytesIO
import json

from src.config.app import config
from src.utils.logging_config import logger


class VLModelClient:
    """视觉语言模型客户端"""
    
    def __init__(self):
        self.provider = None
        self.model_name = None
        self.base_url = None
        self.api_key = None
        self._setup_model()
    
    def _setup_model(self):
        """设置VL模型配置"""
        vl_model_spec = config.vl_model
        if not vl_model_spec:
            logger.warning("未配置VL模型，无法使用图片描述功能")
            return
        
        try:
            # 解析模型规格：provider/model_name
            if "/" in vl_model_spec:
                provider, model_name = vl_model_spec.split("/", 1)
            else:
                provider = vl_model_spec
                model_name = None
            
            # 获取模型配置
            if provider not in config.vl_model_names:
                logger.warning(f"VL模型提供商 {provider} 未在配置中定义")
                return
            
            provider_config = config.vl_model_names[provider]
            self.base_url = provider_config.get("base_url")
            
            # 如果没有指定模型名，使用默认模型
            if not model_name:
                model_name = provider_config.get("default")
            
            self.provider = provider
            self.model_name = model_name
            
            # 获取API密钥
            env_var = provider_config.get("env")
            if env_var != "NO_API_KEY":
                self.api_key = os.getenv(env_var)
                if not self.api_key:
                    logger.warning(f"未设置 {env_var} 环境变量，无法使用 {provider} VL模型")
                    return
            
            logger.info(f"VL模型客户端初始化成功: {provider}/{model_name}")
            
        except Exception as e:
            logger.error(f"VL模型客户端初始化失败: {str(e)}")
    
    def is_available(self) -> bool:
        """检查VL模型是否可用"""
        return all([self.provider, self.model_name, self.base_url])
    
    def _image_to_base64(self, image_path: str) -> str:
        """将图片转换为base64编码"""
        try:
            # 判断是否为URL
            if image_path.startswith(('http://', 'https://')):
                # 特殊处理：如果是本地服务器图片，尝试直接读取本地文件
                if image_path.startswith('http://localhost:5050/api/system/images/'):
                    # 提取文件名
                    filename = image_path.split('/')[-1]
                    # 构建本地文件路径
                    local_path = os.path.join("saves", "chat_images", filename)
                    if os.path.exists(local_path):
                        # 直接从本地文件读取，避免网络请求
                        with open(local_path, 'rb') as f:
                            image_data = f.read()
                    else:
                        # 如果本地文件不存在，回退到网络下载
                        response = requests.get(image_path, timeout=10)
                        response.raise_for_status()
                        image_data = response.content
                else:
                    # 其他网络URL，正常下载
                    response = requests.get(image_path, timeout=10)
                    response.raise_for_status()
                    image_data = response.content
            else:
                # 从本地文件读取图片
                with open(image_path, 'rb') as f:
                    image_data = f.read()
            
            # 转换为base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return base64_data
            
        except Exception as e:
            raise ValueError(f"无法加载图片: {image_path}，错误: {str(e)}")
    
    def get_image_description(self, image_path: str, prompt: Optional[str] = None) -> str:
        """获取图片描述
        
        Args:
            image_path: 图片路径（本地文件路径或URL）
            prompt: 可选的提示词，用于指导模型生成描述
            
        Returns:
            str: 图片描述文本
        """
        if not self.is_available():
            raise RuntimeError("VL模型不可用，请检查配置")
        
        try:
            # 将图片转换为base64
            base64_image = self._image_to_base64(image_path)
            
            # 构建请求数据
            if self.provider == "ark":
                # 豆包模型API格式
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt or "请详细描述这张图片的内容、场景、物体、颜色、风格等特征"
                            }
                        ]
                    }
                ]
                
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                description = result["choices"][0]["message"]["content"]
                
            else:
                # 其他VL模型提供商（可根据需要扩展）
                raise NotImplementedError(f"暂不支持 {self.provider} 类型的VL模型")
            
            logger.info(f"VL模型图片描述生成成功")
            return description.strip()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"VL模型API请求失败: {str(e)}")
            raise RuntimeError(f"VL模型API请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"VL模型图片描述生成失败: {str(e)}")
            raise RuntimeError(f"VL模型图片描述生成失败: {str(e)}")


# 全局VL模型客户端实例
vl_client = VLModelClient()