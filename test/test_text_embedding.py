#!/usr/bin/env python3
"""
测试get_text_embedding方法的可行性
"""

import os
import sys
import numpy as np

from pathlib import Path
# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.knowledge.utils.image_embedding_utils import get_text_embedding

def test_text_embedding():
    """测试文本嵌入功能"""
    print("=== 测试get_text_embedding方法 ===")
    text = "这是一件玉器，呈圆形玉璧状，玉质温润泛白，饰有连续卷云（回纹）纹样，工艺古朴雅致。关键字：玉器，玉璧，卷云纹，古玉，圆形"
    embedding = get_text_embedding(text)
    print("嵌入向量形状:", embedding.shape)
    
   


def main():
    """主测试函数"""
    print("开始测试get_text_embedding方法...\n")
    
    # 测试基本功能
    test_text_embedding()
    

if __name__ == "__main__":
    main()