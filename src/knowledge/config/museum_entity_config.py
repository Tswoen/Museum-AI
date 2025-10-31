"""
博物馆文物领域的实体和关系类型配置
"""

# 博物馆文物领域的实体类型定义
MUSEUM_ENTITY_TYPES = [
    "Artifact",     # 文物
    "Period",        # 时代
    "Site",          # 出土地
    "Category",      # 类别
    "Material",      # 材质
    "Function",      # 功能
    "Person",        # 相关人物
    "State",         # 国别
    "Exhibition",    # 展览
    "Theme",         # 主题
    "Ritual"         # 仪式
]

# 实体类型描述
ENTITY_DESCRIPTIONS = {
    "Artifact": "文物、艺术品、考古发现等实物",
    "Period": "历史时期、年代、时代",
    "Site": "考古遗址、出土地点、发现地点",
    "Category": "文物分类、类型、类别",
    "Material": "制作材料、材质、原料",
    "Function": "功能用途、使用目的",
    "Person": "相关人物、创作者、使用者",
    "State": "国家、朝代、政权",
    "Exhibition": "展览、展出活动、展示场所",
    "Theme": "主题、题材、内容",
    "Ritual": "仪式、礼仪、习俗"
}

# 博物馆文物领域的关系类型定义
MUSEUM_RELATION_TYPES = [
    "belongs_to",      # 属于
    "created_in",      # 创作于
    "discovered_at",   # 发现于
    "made_of",        # 由...制成
    "used_for",       # 用于
    "related_to",     # 与...相关
    "exhibited_in",   # 展览于
    "part_of",        # 是...的一部分
    "influenced_by",  # 受...影响
    "represents"      # 代表
]

# 关系类型描述
RELATION_DESCRIPTIONS = {
    "belongs_to": "表示实体属于某个类别或分类",
    "created_in": "表示实体在特定时期或时代被创作或制作",
    "discovered_at": "表示实体在特定地点被发现或出土",
    "made_of": "表示实体由特定材料制成",
    "used_for": "表示实体具有特定功能或用途",
    "related_to": "表示实体之间存在一般性关联",
    "exhibited_in": "表示实体在特定展览中展出",
    "part_of": "表示实体是另一个实体的一部分",
    "influenced_by": "表示实体受到其他实体的影响",
    "represents": "表示实体代表或体现某种主题或概念"
}

# 博物馆文物领域的特定关系映射
MUSEUM_SPECIFIC_RELATIONS = {
    # 文物与类别的关系
    "Artifact -> Category": "belongs_to",
    # 文物与出土地的关系  
    "Artifact -> Site": "discovered_at",
    # 文物与时代的关系
    "Artifact -> Period": "created_in",
    # 文物与功能的关系
    "Artifact -> Function": "used_for",
    # 文物与材质的关系
    "Artifact -> Material": "made_of",
    # 文物与展览的关系
    "Artifact -> Exhibition": "exhibited_in",
    # 文物与国家的关系
    "Artifact -> State": "related_to",
    # 文物与人物的关系
    "Artifact -> Person": "related_to",
    # 文物与文物的关系
    "Artifact -> Artifact": "related_to",
    # 展览与主题的关系
    "Exhibition -> Theme": "represents"
}

# 实体提取提示词模板
ENTITY_EXTRACTION_PROMPT = """
请从文本中提取博物馆文物领域的实体和关系。重点关注以下实体类型：
- 文物 (Artifact): 具体的文物、艺术品、考古发现
- 时代 (Period): 历史时期、年代
- 出土地 (Site): 考古遗址、发现地点
- 类别 (Category): 文物分类
- 材质 (Material): 制作材料
- 功能 (Function): 用途功能
- 人物 (Person): 相关人物
- 国别 (State): 国家朝代
- 展览 (Exhibition): 展览活动
- 主题 (Theme): 主题内容
- 仪式 (Ritual): 仪式习俗

关系类型包括：属于、创作于、发现于、由...制成、用于、与...相关、展览于、是...的一部分、受...影响、代表等。
"""

def get_museum_entity_config():
    """获取博物馆文物领域的完整配置"""
    return {
        "entity_types": MUSEUM_ENTITY_TYPES,
        "relation_types": MUSEUM_RELATION_TYPES,
        "entity_descriptions": ENTITY_DESCRIPTIONS,
        "relation_descriptions": RELATION_DESCRIPTIONS,
        "specific_relations": MUSEUM_SPECIFIC_RELATIONS,
        "extraction_prompt": ENTITY_EXTRACTION_PROMPT
    }

if __name__ == "__main__":
    config = get_museum_entity_config()
    print("博物馆文物领域配置:")
    print(f"实体类型: {config['entity_types']}")
    print(f"关系类型: {config['relation_types']}")