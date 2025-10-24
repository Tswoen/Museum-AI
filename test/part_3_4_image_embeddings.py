database_path = "milvus_db/milvus.db"  # 定义 Milvus 数据库的路径

# from part_3_1_milvus_util import milvus_util  # 导入自定义的 Milvus 工具类

# collection_name = milvus_util.IMAGE_COLLECTION_NAME  # 获取图片集合的名称



import torch  # PyTorch 深度学习框架
from PIL import Image  # 图像处理库
import cn_clip.clip as clip  # 中文 CLIP 库
from cn_clip.clip import load_from_name, available_models  # CLIP 相关方法
import torch  # 再次导入 torch（可省略）
import os  # 操作系统相关
import json  # 处理 JSON 文件
from cn_clip.clip.utils import create_model, image_transform  # CLIP 工具方法

# 判断是否有可用的 GPU，否则使用 CPU
device = "cuda" if torch.cuda.is_available() else "cpu"

# 获取图像预处理方法
preprocess = image_transform()

# 指定预训练模型的路径
import os
pre_train_model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves", "model", "clip_finetune", "checkpoints", "best.pt")

# 加载预训练模型参数
pretrained = torch.load(pre_train_model_path, map_location='cpu')
print("1 加载模型成功")
# 创建中文 CLIP 模型并加载权重
model = create_model("ViT-B-16@RoBERTa-wwm-ext-base-chinese", checkpoint=pretrained)

# 将模型移动到指定设备（GPU 或 CPU）并设置为评估模式
model = model.to(device)
print("2 模型移动到设备成功")
model.eval()

def get_image_embedding(image_path, model, preprocess):
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(model.logit_scale.device)  # 读取图片并预处理，增加 batch 维度，移动到模型设备
    with torch.no_grad():  # 关闭梯度计算，节省内存
        image_features = model.encode_image(image)  # 提取图片特征
        image_features /= image_features.norm(dim=-1, keepdim=True)  # 特征归一化
    return image_features.cpu().numpy().astype('float32').flatten()  # 转为 numpy 数组并展平成一维

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
def get_text_main_content(text):
    # 查找【外观特征】和【保存状况】的起止位置
    start = text.find("【外观特征】")
    end = text.find("【保存状况】")
    if start == -1 or end == -1:
        return ""  # 如果找不到，返回空字符串
    content = text[start + len("【外观特征】"):end].strip()  # 截取【外观特征】部分
    # 按行分割内容
    lines = content.split("\n")
    main_content = []
    for line in lines:
        line = line.strip()
        # 只处理以 1. 2. 3. 开头的行
        if line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
            # 去掉序号和字段名，只保留冒号后的内容
            sentence = line.split("：", 1)[-1].strip()
            # 去除末尾句号
            if sentence.endswith("。"):
                sentence = sentence[:-1]
            main_content.append(sentence)
    # 合并为一个字符串，用分号隔开，结尾加句号
    return "；".join(main_content)+"。"

data_path = "dataset/final"  # 数据集所在目录

for filename in os.listdir(data_path):  # 遍历数据集目录下所有文件
    if filename.endswith(".json") and filename.startswith("data"):  # 只处理以 data 开头、.json 结尾的文件
        file_path = os.path.join(data_path, filename)  # 构建文件完整路径
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)  # 读取 JSON 文件内容
            print(f"Processing file: {file_path}")  # 打印正在处理的文件
            images = data.get("images", [])  # 获取图片文件名列表
            insert_data_list = []  # 存储待插入 Milvus 的数据
            # 遍历每一张图片，提取图片 embedding
            for image in images:
                artifact_id = data.get("artifact_id", "")  # 文物 ID
                category = data.get("category", "")  # 文物类别
                era = data.get("era", "")  # 文物年代
                name = data.get("name", "")  # 文物名称
                image_path = os.path.join(data_path, "images", image)  # 构建图片路径
                embedding = get_image_embedding(image_path, model, preprocess)  # 获取图片 embedding
                insert_data_list.append({
                    "artifact_id": artifact_id,  # 文物 ID
                    "embedding": embedding,  # 图片特征向量
                    "category": category,  # 类别
                    "era": era,  # 年代
                    "name": name,  # 名称
                    "image_path": image_path  # 图片路径
                })
            # 处理每一条图片描述，提取文本 embedding
            image_descriptions = data['image_descriptions']  # 获取图片描述列表
            for description in image_descriptions:
                image_name = description['image_name']  # 图片文件名
                text = description['description']  # 描述文本
                text = get_text_main_content(text)  # 提取主要内容
                text_embedding = get_text_embedding(text, model)  # 获取文本 embedding
                image_path = os.path.join(data_path, "images", image_name)  # 构建图片路径
                insert_data_list.append({
                    "artifact_id": artifact_id,  # 文物 ID
                    "embedding": text_embedding,  # 文本特征向量
                    "category": category,  # 类别
                    "era": era,  # 年代
                    "name": name,  # 名称
                    "image_path": image_path  # 图片路径
                })

            # 如果有数据，批量插入到 Milvus 数据库
            if insert_data_list:
                milvus_util.insert_data(collection_name=collection_name, data=insert_data_list)  # 插入数据
                print(f"Inserted {len(insert_data_list)} images from {filename} into Milvus collection.")  # 打印插入结果




    
