"""
博物馆文物领域实体和关系类型配置
用于配置LightRAG在add_content时识别的特定实体和关系类型
"""

# 博物馆文物领域实体类型定义
MUSEUM_ENTITY_TYPES = [
    "Artifact",      # 文物
    "Period",        # 时代
    "Site",          # 出土地
    "Category",      # 类别
    "Material",      # 材质
    "Function",      # 功能
    "Person",        # 相关人物
    "State",         # 国别
    "Exhibition",    # 展览
    "Theme",         # 主题/仪式
]

# 博物馆文物领域关系类型定义
MUSEUM_RELATION_TYPES = [
    "属于",           # Artifact → Category
    "出土于",         # Artifact → Site
    "制作于",         # Artifact → Period
    "使用于",         # Artifact → Function
    "材质为",         # Artifact → Material
    "展示于",         # Artifact → Exhibition
    "相关国家",       # Artifact → State
    "关联人物",       # Artifact → Person
    "同类文物",       # Artifact ↔ Artifact
    "主题相关",       # Exhibition ↔ Theme
]

# 实体类型描述映射（用于LLM理解实体类型含义）
ENTITY_TYPE_DESCRIPTIONS = {
    "Artifact": "文物，包括各种古代器物、艺术品、考古发现等",
    "Period": "时代，指文物所属的历史时期或年代",
    "Site": "出土地，文物被发现或出土的具体地点",
    "Category": "类别，文物的分类，如陶器、青铜器、玉器等",
    "Material": "材质，文物制作所用的材料",
    "Function": "功能，文物的用途或功能",
    "Person": "相关人物，与文物相关的历史人物、制作者、使用者等",
    "State": "国别，文物所属的国家或地区",
    "Exhibition": "展览，文物展出或收藏的展览或博物馆",
    "Theme": "主题/仪式，与文物相关的文化主题、仪式或象征意义",
}

# 关系类型描述映射
RELATION_TYPE_DESCRIPTIONS = {
    "属于": "表示文物属于某个类别",
    "出土于": "表示文物出土于某个地点",
    "制作于": "表示文物制作于某个时代",
    "使用于": "表示文物用于某种功能",
    "材质为": "表示文物由某种材质制成",
    "展示于": "表示文物在某个展览中展示",
    "相关国家": "表示文物与某个国家相关",
    "关联人物": "表示文物与某个人物相关",
    "同类文物": "表示两个文物属于同一类型或具有相似特征",
    "主题相关": "表示展览与某个主题相关",
}

# 实体提取提示词模板（用于增强LLM对博物馆领域的理解）
MUSEUM_ENTITY_EXTRACTION_PROMPT = """
你是一个专业的博物馆文物知识图谱构建专家。请从以下文本中提取与博物馆文物相关的实体和关系。

重点关注以下实体类型：
- 文物 (Artifact): 各种古代器物、艺术品、考古发现
- 时代 (Period): 文物所属的历史时期或年代
- 出土地 (Site): 文物被发现或出土的具体地点
- 类别 (Category): 文物的分类，如陶器、青铜器、玉器等
- 材质 (Material): 文物制作所用的材料
- 功能 (Function): 文物的用途或功能
- 相关人物 (Person): 与文物相关的历史人物、制作者、使用者等
- 国别 (State): 文物所属的国家或地区
- 展览 (Exhibition): 文物展出或收藏的展览或博物馆
- 主题 (Theme): 与文物相关的文化主题、仪式或象征意义

关系类型包括：属于、出土于、制作于、使用于、材质为、展示于、相关国家、关联人物、同类文物、主题相关。

请仔细分析文本，提取所有相关的实体和关系。"""

def get_museum_entity_config():
    """
    获取博物馆文物领域的实体配置
    """
    return {
        "entity_types": MUSEUM_ENTITY_TYPES,
        "relation_types": MUSEUM_RELATION_TYPES,
        "entity_descriptions": ENTITY_TYPE_DESCRIPTIONS,
        "relation_descriptions": RELATION_TYPE_DESCRIPTIONS,
        "custom_prompt": MUSEUM_ENTITY_EXTRACTION_PROMPT
    }

def create_lightrag_config():
    """
    创建适用于LightRAG的配置字典
    """
    return {
        "addon_params": {
            "entity_types": MUSEUM_ENTITY_TYPES,
            "language": "Chinese",
            "museum_domain": True
        }
    }

if __name__ == "__main__":
    config = get_museum_entity_config()
    print("博物馆文物领域实体配置:")
    print(f"实体类型: {config['entity_types']}")
    print(f"关系类型: {config['relation_types']}")