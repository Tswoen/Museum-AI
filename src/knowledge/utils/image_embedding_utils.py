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

# 获取图像预处理方法
# def get_image_embedding(image_path, clip_model = None, preprocess = None):
#     if preprocess is None:
#         preprocess = image_transform()
#     if clip_model is None:
#         clip_model = model
#     image = preprocess(Image.open(image_path)).unsqueeze(0).to(clip_model.logit_scale.device)  # 读取图片并预处理，增加 batch 维度，移动到模型设备
#     with torch.no_grad():  # 关闭梯度计算，节省内存
#         image_features = clip_model.encode_image(image)  # 提取图片特征
#         image_features /= image_features.norm(dim=-1, keepdim=True)  # 特征归一化
#     return image_features.cpu().numpy().astype('float32').flatten()  # 转为 numpy 数组并展平成一维

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

def get_text_embedding(text, model):
    text = clip.tokenize([text]).to(device)  # 对文本进行分词并转为张量，移动到设备
    with torch.no_grad():  # 关闭梯度计算
        text_features = model.encode_text(text)  # 提取文本特征
        text_features /= text_features.norm(dim=-1, keepdim=True)  # 特征归一化
    return text_features.cpu().numpy().astype('float32').flatten()  # 转为 numpy 数组并展平成一维

# 用于从文本中提取主要内容的函数
# 【文物名称】南山四皓画像砖\n\n【外观特征】\n1. 整体形制：长方形，厚实，上宽下窄，有明显的凸起部分。\n2. 材质：灰白色，可能为泥质石或者陶质。\n3. 装饰纹样：浮雕表现南山四皓在竹林中闲聊的场景，人物线条细腻，背景有树木和人物装饰，整体风格古朴。\n\n【保存状况】\n保存较为完好，表面有一些自然风化的痕迹，但没有明显的修复痕迹。


# 格式如上，仅获取 【外观特征】整体形制 材质 装饰纹样 中的这3个主要内容，并且去 整体形制 材质 装饰纹样 这3个词和前面开头的 序号
# 最终得到的结果 为 长方形，厚实，上宽下窄，有明显的凸起部分；灰白色，可能为泥质石或者陶质；浮雕表现南山四皓在竹林中闲聊的场景，人物线条细腻，背景有树木和人物装饰，整体风格古朴。

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