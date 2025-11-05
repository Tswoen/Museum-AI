import torch 
from PIL import Image
import numpy as np
import os

import cn_clip.clip as clip
from cn_clip.clip import load_from_name, available_models
print("Available models:", available_models())  
# Available models: ['ViT-B-16', 'ViT-L-14', 'ViT-L-14-336', 'ViT-H-14', 'RN50']

device = "cuda" if torch.cuda.is_available() else "cpu"
# 如本地模型不存在，自动从ModelScope下载模型，需要提前安装`modelscope`包
download_root = "D:\studyroom\projectspace\AIAgent_project\Museum-AI\saves\model\clip_github_before_finetune"
model, preprocess = load_from_name("ViT-B-16", device=device, download_root=download_root, use_modelscope=True)
model.eval()

def compare_singleImg_multiText():
    img_path = "D:\studyroom\projectspace\AIAgent_project\Museum-AI\saves\imgs\yuyuan.jpg"
    image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
    text_list = [
                "一个玉器",
                "温润的玉料雕琢而成，整体呈弯曲状，前端似禽鸟头部造型，后端设方形钮，用于固定在衣物上，功能类似现代的皮带扣", 
                "汉代玉带钩",
                "玉带钩"
                ]
    text = clip.tokenize(text_list).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text)
        # 对特征进行归一化，请使用归一化后的图文特征用于下游任务
        image_features /= image_features.norm(dim=-1, keepdim=True) 
        text_features /= text_features.norm(dim=-1, keepdim=True)    

        logits_per_image, logits_per_text = model.get_similarity(image, text)
        probs = logits_per_image.softmax(dim=-1).cpu().numpy()

    # print("Label probs:", probs)  # [[1.268734e-03 5.436878e-02 6.795761e-04 9.436829e-01]]

    # 方法1：设置numpy的打印格式
    np.set_printoptions(suppress=True, precision=6)
    print("概率结果:", probs)
def compare_multiImg_singleText():
    # 准备多张图片
    image_paths = [
        "D:\\studyroom\\projectspace\\AIAgent_project\\Museum-AI\\saves\\imgs\\yuyuan.jpg",
        "D:\\studyroom\\projectspace\\AIAgent_project\\Museum-AI\\saves\\imgs\\qingyuloukong.jpg",
        "D:\\studyroom\\projectspace\\AIAgent_project\\Museum-AI\\saves\\imgs\\QQ20251024-172103.png",
    ]

    # 只保留存在的图片路径
    valid_image_paths = [path for path in image_paths if os.path.exists(path)]
    print(f"找到 {len(valid_image_paths)} 张图片")

    # 预处理所有图片
    image_tensors = []
    for path in valid_image_paths:
        try:
            img_tensor = preprocess(Image.open(path)).unsqueeze(0)
            image_tensors.append(img_tensor)
        except Exception as e:
            print(f"无法加载图片 {path}: {e}")

    if not image_tensors:
        print("没有可用的图片")
        return

    # 将图片堆叠成批次
    image_batch = torch.cat(image_tensors, dim=0).to(device)
    print(f"图片批次形状: {image_batch.shape}")

    # 单个文本
    text_description = "形状像钩子的玉器"
    text_tensor = clip.tokenize([text_description]).to(device)
    print(f"文本: '{text_description}'")
    print(f"文本张量形状: {text_tensor.shape}")

    print("\n=== 文本与多张图片相似度结果（批量计算）===")
    print("-" * 50)

    with torch.no_grad():
        # 批量编码所有图片
        image_features = model.encode_image(image_batch)
        # 编码文本
        text_features = model.encode_text(text_tensor)
        
        # 归一化特征
        image_features /= image_features.norm(dim=-1, keepdim=True) 
        text_features /= text_features.norm(dim=-1, keepdim=True)
        
        # 计算相似度（使用与CLIP相同的方法）
        # 相似度 = 图像特征 · 文本特征^T * exp(logit_scale)
        logit_scale = model.logit_scale.exp()
        logits_per_image = (image_features @ text_features.T) * logit_scale
        
        # 在图像维度上做softmax，得到每张图片相对于该文本的概率
        probs = logits_per_image.softmax(dim=0).cpu().numpy()

    # 收集结果
    all_results = []
    for i, path in enumerate(valid_image_paths):
        prob_value = probs[i][0]  # 因为只有一个文本
        all_results.append((path, prob_value))
        
        print(f"图片 {i+1}: {os.path.basename(path)}")
        print(f"相似度概率: {prob_value:.6f} ({prob_value*100:.2f}%)")
        print()

    # 按相似度排序
    all_results.sort(key=lambda x: x[1], reverse=True)
    
    print("\n=== 排序结果（从高到低）===")
    for rank, (path, prob) in enumerate(all_results, 1):
        print(f"排名 {rank}: {prob:.6f} ({prob*100:.2f}%) - {os.path.basename(path)}")

# compare_singleImg_multiText()
compare_multiImg_singleText()