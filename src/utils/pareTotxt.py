import json
import os

def local_json_to_txt(input_json_path, output_txt_path="extracted_local_data.txt"):
    """
    从本地JSON文件读取内容，提取name和description字段生成TXT文件
    :param input_json_path: 本地JSON文件的完整路径（如C:/data/relics.json 或 ./relics.json）
    :param output_txt_path: 输出TXT文件的路径和名称
    """
    try:
        # 1. 校验本地JSON文件是否存在
        if not os.path.exists(input_json_path):
            raise FileNotFoundError(f"本地JSON文件不存在：{input_json_path}")
        if not input_json_path.endswith(".json"):
            raise ValueError("输入文件不是.json格式，请确认文件类型")
        
        # 2. 读取本地JSON文件内容
        print(f"正在读取本地JSON文件：{input_json_path}")
        with open(input_json_path, "r", encoding="utf-8") as json_file:
            json_data = json.load(json_file)
        
        # 3. 检查数据格式（确保是列表结构，匹配原数据格式）
        if not isinstance(json_data, list):
            raise ValueError("JSON文件内容不是列表格式，请确认数据结构（需为[{...}, {...}]形式）")
        
        # 4. 提取name和description字段，组装TXT内容
        txt_content = []
        for idx, item in enumerate(json_data, 1):
            # 字段缺失时用默认值填充，避免报错
            item_name = item.get("name", f"未命名项目_{idx}")
            item_desc = item.get("description", "无描述信息")
            # 按“序号. 名称：描述”格式组装，每条数据占一行
            txt_line = f"{idx}. {item_name}：{item_desc}"
            txt_content.append(txt_line)
        
        # 5. 写入TXT文件
        with open(output_txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write("\n".join(txt_content))
        
        # 6. 输出处理结果
        print(f"处理完成！")
        print(f"- 共提取 {len(txt_content)} 条数据")
        print(f"- TXT文件已保存至：{os.path.abspath(output_txt_path)}")
        # 预览前3条数据，方便快速确认
        print("\n前3条数据预览：")
        for line in txt_content[:3]:
            print(f"  {line}")
    
    except FileNotFoundError as e:
        print(f"文件错误：{str(e)}（请检查JSON文件路径是否正确）")
    except ValueError as e:
        print(f"数据格式错误：{str(e)}")
    except json.JSONDecodeError:
        print("JSON解析失败：文件内容损坏或不符合JSON语法")
    except Exception as e:
        print(f"处理过程中出错：{str(e)}")

# -------------------------- 请修改以下本地文件路径 --------------------------
# 1. 替换为你的本地JSON文件路径（绝对路径或相对路径均可）
# 示例1（绝对路径）：C:/Users/XXX/Documents/relics.json
# 示例2（相对路径，JSON文件与代码在同一文件夹）：./relics.json
LOCAL_JSON_PATH = "D:\studyroom\projectspace\AIAgent_project\Museum-AI\hubei_museum_artifacts.json"  # 这里替换为实际路径
# 2. 可选：自定义输出TXT文件名称（默认是extracted_local_data.txt）
OUTPUT_TXT_NAME = "extracted_local_data.txt"
# ----------------------------------------------------------------------

# 执行本地JSON转TXT操作
if __name__ == "__main__":
    local_json_to_txt(input_json_path=LOCAL_JSON_PATH, output_txt_path=OUTPUT_TXT_NAME)