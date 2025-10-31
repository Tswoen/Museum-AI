"""
测试LightRAG博物馆文物领域实体识别功能
"""

import asyncio
import os
import sys

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.knowledge.implementations.lightrag import LightRagKB
from src.knowledge.config.museum_entity_config import get_museum_entity_config

async def test_entity_recognition():
    """测试实体识别功能"""
    
    # 获取博物馆配置
    config = get_museum_entity_config()
    print("=== 博物馆文物领域配置 ===")
    print(f"实体类型: {config['entity_types']}")
    print(f"关系类型: {config['relation_types']}")
    print()
    
    # 创建测试知识库
    work_dir = "test_lightrag"
    kb = LightRagKB(work_dir)
    
    # 创建测试数据库
    db_id = "test_museum_db"
    
    # 创建数据库配置
    db_config = {
        "name": "测试博物馆知识库",
        "description": "用于测试博物馆文物领域实体识别功能",
        "metadata": {
            "addon_params": {
                "language": "Chinese",
                "entity_types": config['entity_types'],
                "relation_types": config['relation_types']
            }
        }
    }
    
    try:
        # 创建数据库
        result = kb.create_database(db_id, db_config)
        print(f"✅ 数据库创建成功: {result}")
        
        # 测试文本内容
        test_texts = [
            """
            青铜鼎是中国商周时期的重要文物，出土于河南安阳殷墟遗址。
            这件文物属于礼器类别，由青铜材质制成，主要用于祭祀仪式。
            它制作于商代晚期，与商王武丁时期相关，现收藏于中国国家博物馆。
            """,
            """
            唐三彩马俑是唐代陶瓷艺术的代表作，出土于陕西西安。
            这件文物属于随葬品类别，由陶土制成，主要用于墓葬陪葬。
            它制作于唐代开元年间，反映了唐代的丧葬习俗和艺术风格。
            """,
            """
            清明上河图是北宋画家张择端的作品，描绘了汴京城的繁华景象。
            这幅画属于绘画类别，由绢本设色制成，主要功能是艺术表现。
            它创作于北宋时期，现收藏于北京故宫博物院，是重要的文化遗产。
            """
        ]
        
        print("\n=== 开始测试实体识别 ===")
        
        for i, text in enumerate(test_texts, 1):
            print(f"\n--- 测试文本 {i} ---")
            print(f"内容: {text.strip()[:100]}...")
            
            # 添加内容到知识库
            try:
                result = await kb.add_content(db_id, [text], {"content_type": "file"})
                print(f"✅ 内容添加成功")
                
                # 获取知识库实例
                rag_instance = await kb._get_lightrag_instance(db_id)
                if rag_instance:
                    # 查询实体
                    print("📊 实体识别结果:")
                    
                    # 尝试获取实体存储
                    if hasattr(rag_instance, 'entities_vdb'):
                        entities = rag_instance.entities_vdb
                        print(f"实体存储类型: {type(entities)}")
                    
                    # 尝试获取关系存储
                    if hasattr(rag_instance, 'relationships_vdb'):
                        relationships = rag_instance.relationships_vdb
                        print(f"关系存储类型: {type(relationships)}")
                        
            except Exception as e:
                print(f"❌ 内容添加失败: {e}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试数据库
        try:
            kb.delete_database(db_id)
            print("🧹 测试数据库已清理")
        except:
            pass

async def test_lightrag_config():
    """测试LightRAG配置是否正确加载"""
    
    print("=== 测试LightRAG配置 ===")
    
    # 创建测试知识库
    work_dir = "test_config"
    kb = LightRagKB(work_dir)
    
    # 测试配置加载
    db_id = "config_test_db"
    
    try:
        # 创建数据库
        db_config = {
            "name": "配置测试数据库",
            "description": "测试LightRAG配置加载",
            "metadata": {
                "language": "Chinese"
            }
        }
        
        result = kb.create_database(db_id, db_config)
        print(f"✅ 数据库创建成功")
        
        # 获取LightRAG实例
        rag_instance = await kb._create_kb_instance(db_id, {})
        
        if rag_instance:
            print(f"✅ LightRAG实例创建成功")
            
            # 检查配置
            if hasattr(rag_instance, 'addon_params'):
                addon_params = rag_instance.addon_params
                print(f"📋 加载的配置参数:")
                print(f"   语言: {addon_params.get('language', '未设置')}")
                print(f"   实体类型: {addon_params.get('entity_types', [])}")
                print(f"   关系类型: {addon_params.get('relation_types', [])}")
                
                # 验证配置是否正确
                expected_entities = ["Artifact", "Period", "Site", "Category", "Material", 
                                   "Function", "Person", "State", "Exhibition", "Theme", "Ritual"]
                
                actual_entities = addon_params.get('entity_types', [])
                if set(expected_entities) == set(actual_entities):
                    print("✅ 实体类型配置正确")
                else:
                    print("❌ 实体类型配置不匹配")
                    print(f"   期望: {expected_entities}")
                    print(f"   实际: {actual_entities}")
                    
                expected_relations = ["belongs_to", "created_in", "discovered_at", "made_of", 
                                    "used_for", "related_to", "exhibited_in", "part_of", 
                                    "influenced_by", "represents"]
                
                actual_relations = addon_params.get('relation_types', [])
                if set(expected_relations) == set(actual_relations):
                    print("✅ 关系类型配置正确")
                else:
                    print("❌ 关系类型配置不匹配")
                    print(f"   期望: {expected_relations}")
                    print(f"   实际: {actual_relations}")
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        try:
            kb.delete_database(db_id)
            print("🧹 测试数据库已清理")
        except:
            pass

async def main():
    """主测试函数"""
    print("🚀 开始测试LightRAG博物馆文物领域实体识别功能")
    print("=" * 60)
    
    # 测试配置
    await test_lightrag_config()
    
    print("\n" + "=" * 60)
    
    # 测试实体识别
    await test_entity_recognition()
    
    print("\n🎉 所有测试完成")

if __name__ == "__main__":
    asyncio.run(main())