from PIL import Image  # 图像处理库
import cn_clip.clip as clip  # 中文 CLIP 库
from cn_clip.clip import load_from_name, available_models  # CLIP 相关方法
import torch  # 再次导入 torch（可省略）
import os  # 操作系统相关
import json  # 处理 JSON 文件
from cn_clip.clip.utils import  image_transform  # CLIP 工具方法
from src.models.cn_clip_model import model
import requests
from io import BytesIO
from pathlib import Path
from src.models.vl_model_client import vl_client
from src.utils.logging_config import logger

def get_image_description(image_path):
    """
    从图片中提取描述信息，优先使用VL模型，失败时回退到基础分析

    Args:
        image_path (str): 图片路径

    Returns:
        str: 图片描述信息
    """
    # 优先使用VL模型生成描述
    if vl_client.is_available():
        try:
            # 针对文物图片的特殊提示词
            prompt = """请详细描述这张图片，
            首先用50字以内描述如下内容：
1. 文物的材质类型（如青铜、玉器等）
2. 外观特征（形状、尺寸、材质、颜色）
3. 装饰纹样和图案
然后再给出大约5个关键字（用逗号分隔）

注意：1.请用中文回答，描述要详细且专业。2.按照以下结构化格式输出：这里是图片的描述。\n关键字：这里是几个关键字
    
"""
            
            description = vl_client.get_image_description(image_path, prompt)
            logger.info("使用VL模型成功生成图片描述")
            return description
            
        except Exception as e:
            logger.warning(f"VL模型生成描述失败，回退到基础分析: {str(e)}")
    
    # VL模型不可用或失败时，回退到基础分析
    return _get_basic_image_description(image_path)


def _get_basic_image_description(image_path):
    """
    基础图片描述分析（VL模型不可用时的回退方案）
    
    Args:
        image_path (str): 图片路径
        
    Returns:
        str: 基础图片描述
    """
    try:
        # 加载图片
        if image_path.startswith(('http://', 'https://')):
            # 特殊处理：如果是本地服务器图片，尝试直接读取本地文件
            if image_path.startswith('http://localhost:5050/api/system/images/'):
                # 提取文件名
                filename = image_path.split('/')[-1]
                # 构建本地文件路径
                local_path = Path("saves/chat_images") / filename
                if local_path.exists():
                    # 直接从本地文件读取，避免网络请求
                    image = Image.open(local_path)
                else:
                    # 如果本地文件不存在，回退到网络下载
                    response = requests.get(image_path, timeout=10)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
            else:
                # 其他网络URL，正常下载
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
        else:
            # 从本地文件读取图片
            image = Image.open(image_path)
        
        # 确保图片是RGB格式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 分析图片基本信息
        width, height = image.size
        format_info = image.format or "未知格式"
        mode_info = image.mode
        
        # 计算图片亮度特征
        grayscale = image.convert('L')
        brightness = sum(grayscale.getdata()) / (width * height)
        
        # 判断图片方向
        orientation = "横向" if width > height else "纵向" if height > width else "正方形"
        
        # 判断图片分辨率
        resolution = "高分辨率" if width * height > 2000000 else "中等分辨率" if width * height > 500000 else "低分辨率"
        
        # 判断亮度水平
        brightness_level = "明亮" if brightness > 200 else "中等亮度" if brightness > 100 else "较暗"
        
        # 构建基础描述
        description = f"图片基本信息：尺寸{width}x{height}像素（{orientation}，{resolution}），格式为{format_info}，颜色模式为{mode_info}，亮度为{brightness_level}。"
        
        # 如果是文物相关图片，添加特殊提示
        if any(keyword in str(image_path).lower() for keyword in ['文物', '古董', '博物馆', 'artifact', 'relic']):
            description += " 检测到可能是文物图片，建议使用VL模型获取更详细的描述。"
        
        logger.info("使用基础分析生成图片描述")
        return description
        
    except Exception as e:
        logger.error(f"基础图片分析失败: {str(e)}")
        return f"无法分析图片: {str(e)}"


def get_image_embedding(image_path, clip_model=None, preprocess=None):
    """
    提取图片的特征嵌入，支持本地文件路径和网络URL
    
    Args:
        image_path (str): 本地图片路径或网络图片URL
        clip_model: CLIP模型，如果为None则使用全局model
        preprocess: 图像预处理函数，如果为None则使用默认预处理
    
    Returns:
        numpy.ndarray: 归一化后的图像特征向量
    """
    if preprocess is None:
        preprocess = image_transform()
    if clip_model is None:
        clip_model = model
    try:
        # 判断是否为URL
        if image_path.startswith(('http://', 'https://')):
            # 特殊处理：如果是本地服务器图片，尝试直接读取本地文件
            if image_path.startswith('http://localhost:5050/api/system/images/'):
                # 提取文件名
                filename = image_path.split('/')[-1]
                # 构建本地文件路径
                local_path = Path("saves/chat_images") / filename
                if local_path.exists():
                    # 直接从本地文件读取，避免网络请求
                    image = Image.open(local_path)
                else:
                    # 如果本地文件不存在，回退到网络下载
                    response = requests.get(image_path, timeout=10)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
            else:
                # 其他网络URL，正常下载
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()  # 检查请求是否成功
                image = Image.open(BytesIO(response.content))
        else:
            # 从本地文件读取图片
            image = Image.open(image_path)
        
        # 确保图片是RGB格式
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
    except Exception as e:
        raise ValueError(f"无法加载图片: {image_path}，错误: {str(e)}")
    
    # 预处理图片并提取特征
    image_tensor = preprocess(image).unsqueeze(0).to(clip_model.logit_scale.device)
    
    with torch.no_grad():
        image_features = clip_model.encode_image(image_tensor)
        image_features /= image_features.norm(dim=-1, keepdim=True)  # 特征归一化
    
    return image_features.cpu().numpy().astype('float32').flatten()

def get_text_embedding(text):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    text = clip.tokenize([text]).to(device)  # 对文本进行分词并转为张量，移动到设备
    with torch.no_grad():  # 关闭梯度计算
        text_features = model.encode_text(text)  # 提取文本特征
        text_features /= text_features.norm(dim=-1, keepdim=True)  # 特征归一化
    return text_features.cpu().numpy().astype('float32').flatten()  # 转为 numpy 数组并展平成一维

def get_img(image_path):
    try:
        # 判断是否为URL
        if image_path.startswith(('http://', 'https://')):
            # 特殊处理：如果是本地服务器图片，尝试直接读取本地文件
            if image_path.startswith('http://localhost:8000/api/system/images/'):
                # 提取文件名
                filename = image_path.split('/')[-1]
                # 构建本地文件路径
                local_path = Path("saves/chat_images") / filename
                if local_path.exists():
                    # 直接从本地文件读取，避免网络请求
                    image = Image.open(local_path)
                else:
                    # 如果本地文件不存在，回退到网络下载
                    response = requests.get(image_path, timeout=10)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
            else:
                # 其他网络URL，正常下载
                response = requests.get(image_path, timeout=10)
                response.raise_for_status()  # 检查请求是否成功
                image = Image.open(BytesIO(response.content))
        else:
            # 从本地文件读取图片
            image = Image.open(image_path)
        print(image)
    except Exception as e:
        raise ValueError(f"无法加载图片: {image_path}，错误: {str(e)}")

if __name__ == "__main__":
    get_img("http://localhost:8000/api/system/images/c8e4197acf3f4de2b8614497d75fc032.png")