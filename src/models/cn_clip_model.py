import torch  # PyTorch 深度学习框架
from PIL import Image  # 图像处理库
import cn_clip.clip as clip  # 中文 CLIP 库
from cn_clip.clip import load_from_name, available_models  # CLIP 相关方法
import torch  # 再次导入 torch（可省略）
import os  # 操作系统相关
import json  # 处理 JSON 文件
from cn_clip.clip.utils import create_model, image_transform  # CLIP 工具方法
from pathlib import Path
from src.utils import logger

# 判断是否有可用的 GPU，否则使用 CPU
device = "cuda" if torch.cuda.is_available() else "cpu"

# 指定预训练模型的路径
import os
# pre_train_model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves", "model", "clip_finetune", "checkpoints", "best.pt")
pre_train_model_path = str(Path("saves/model/clip_finetune/checkpoints/best.pt"))
# 加载预训练模型参数
pretrained = torch.load(pre_train_model_path, map_location='cpu')
logger.info("加载cn-clip模型参数成功")
# 创建中文 CLIP 模型并加载权重
model = create_model("ViT-B-16@RoBERTa-wwm-ext-base-chinese", checkpoint=pretrained)
logger.info("创建cn-clip模型成功")
# 将模型移动到指定设备（GPU 或 CPU）并设置为评估模式
model = model.to(device)
logger.info("将cn-clip模型移动到设备成功")
model.eval()
logger.info("将cn-clip模型设置为评估模式成功")

__all__ = [
    "model"
]