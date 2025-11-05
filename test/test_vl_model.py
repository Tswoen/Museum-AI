#!/usr/bin/env python3
"""
测试VL模型配置和图片描述功能
"""

import os
import sys

from pathlib import Path
# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.app import config
from src.models.vl_model_client import vl_client
from src.knowledge.utils.image_embedding_utils import get_image_description

def test_config():
    """测试配置加载"""
    print("=== 测试配置加载 ===")
    print(f"VL模型配置: {config.vl_model}")
    print(f"VL模型提供商状态: {config.vl_model_provider_status}")
    print(f"可用的VL模型提供商: {config.valuable_vl_model_provider}")
    print(f"VL模型配置详情: {config.vl_model_names}")
    print()

def test_vl_client():
    """测试VL模型客户端"""
    print("=== 测试VL模型客户端 ===")
    print(f"VL客户端是否可用: {vl_client.is_available()}")
    if vl_client.is_available():
        print(f"VL模型提供商: {vl_client.provider}")
        print(f"VL模型名称: {vl_client.model_name}")
        print(f"VL模型基础URL: {vl_client.base_url}")
    print()

def test_image_description():
    """测试图片描述功能"""
    print("=== 测试图片描述功能 ===")
    
    # 测试图片路径（这里使用一个示例图片URL，实际使用时需要替换为真实图片）
    test_image_url = "D:\studyroom\projectspace\AIAgent_project\Museum-AI\saves\imgs\yuyuan.jpg"  # 随机图片生成器
    
    try:
        print(f"测试图片URL: {test_image_url}")
        description = get_image_description(test_image_url)
        print(f"图片描述结果: {description}")
    except Exception as e:
        print(f"图片描述测试失败: {str(e)}")
    print()

def main():
    """主测试函数"""
    print("VL模型功能测试开始...\n")
    
    # 测试配置
    test_config()
    
    # 测试VL客户端
    test_vl_client()
    
    # 测试图片描述功能
    test_image_description()
    
    print("VL模型功能测试完成！")

if __name__ == "__main__":
    main()