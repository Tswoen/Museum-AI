"""
ChromaDB 知识库功能测试
测试 ChromaKB 的基本功能：初始化、创建数据库、添加文档、查询检索
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.knowledge.implementations.chroma import ChromaKB
from src.utils.logging_config import logger
from src import config, knowledge_base
from src.knowledge import KnowledgeBaseManager
from src.knowledge.utils.image_embedding_utils import get_image_embedding

class ChromaDBTester:
    """ChromaDB 测试类"""
    
    def __init__(self):
        """初始化测试环境"""
        # 创建临时工作目录
        self.temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
        self.kb = None
        # database_info = knowledge_base.create_database(
        #     "湖北省博物馆文物知识库", "湖北省博物馆珍贵文物藏品知识库，包含玉器、青铜器、乐器等各类文物信息", kb_type="chroma"
        # )
        self.test_db_id = ""
        
        logger.info(f"测试环境初始化完成，工作目录: {self.temp_dir}")
    
    async def setup(self):
        """设置测试环境"""
        try:
            # 初始化 ChromaKB
            # work_dir = os.path.join(config.save_dir, "knowledge_base_data")
            # knowledge_base = KnowledgeBaseManager(work_dir)
            # self.kb = knowledge_base._get_kb_for_database(self.test_db_id)
            # logger.info("ChromaKB 初始化成功")
            return True
        except Exception as e:
            logger.error(f"ChromaKB 初始化失败: {e}")
            return False
    
    async def test_create_database(self):
        """测试创建数据库"""
        logger.info("=== 测试创建数据库 ===")
        
        try:
            # 创建博物馆文物知识库
            work_dir = os.path.join(config.save_dir, "knowledge_base_data")
            knowledge_base = KnowledgeBaseManager(work_dir)
            db_info = await knowledge_base.create_database(
            "湖北省博物馆文物知识库", "湖北省博物馆珍贵文物藏品知识库，包含玉器、青铜器、乐器等各类文物信息", kb_type="chroma"
        )
            self.test_db_id = db_info['db_id']
            logger.info(f"数据库创建成功: {db_info}")
            logger.info(f"数据库ID: {db_info['db_id']}")
            
            # 初始化 ChromaKB       
            self.kb = knowledge_base._get_kb_for_database(self.test_db_id)
            logger.info("ChromaKB 初始化成功")

            # 验证数据库是否在元数据中
            assert db_info['db_id'] in self.kb.databases_meta
            logger.info("✓ 数据库元数据验证通过")
            
            return True
            
        except Exception as e:
            logger.error(f"创建数据库失败: {e}")
            return False
    
    async def test_add_documents(self):
        """测试添加文档"""
        logger.info("=== 测试添加文档 ===")
        
        try:
            # 检查JSON文件是否存在
            json_file_path = "hubei_museum_artifacts.json"
            if not os.path.exists(json_file_path):
                # 如果在test目录下运行，尝试在上级目录查找
                json_file_path = "../hubei_museum_artifacts.json"
                if not os.path.exists(json_file_path):
                    logger.error(f"找不到文物数据文件: {json_file_path}")
                    return False
            
            logger.info(f"使用文物数据文件: {json_file_path}")
            
            # 直接添加JSON文件到知识库，让add_content方法自动解析
            result = await self.kb.add_content(
                db_id=self.test_db_id,
                items=[json_file_path],
                params={"content_type": "json"}
            )
            
            logger.info(f"文档添加结果: {result}")
            logger.info("✓ 文物JSON文件添加成功")
            
            return True
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    async def test_add_image_embeddings(self):
        """测试添加图片嵌入"""
        logger.info("=== 测试添加图片嵌入 ===")
        
        try:
            # 检查JSON文件是否存在
            json_file_path = "hubei_museum_artifacts.json"
            if not os.path.exists(json_file_path):
                # 如果在test目录下运行，尝试在上级目录查找
                json_file_path = "../hubei_museum_artifacts.json"
                if not os.path.exists(json_file_path):
                    logger.error(f"找不到文物数据文件: {json_file_path}")
                    return False
            
            logger.info(f"使用文物数据文件: {json_file_path}")
            
            # 直接添加JSON文件到知识库，让add_content方法自动解析
            result = await self.kb.add_image_embeddings(
                db_id=self.test_db_id,
                items=[json_file_path],
                params={"content_type": "json"}
            )
            
            logger.info(f"图片嵌入添加结果: {result}")
            logger.info("✓ 文物JSON文件图片嵌入添加成功")
            
            return True
            
        except Exception as e:
            logger.error(f"添加图片嵌入失败: {e}")
            return False

    async def test_query_image_embeddings(self):
        """测试查询图片嵌入"""
        logger.info("=== 测试查询图片嵌入 ===")
        
        try: 
            # 测试博物馆文物相关查询
            test_queries = [
                "https://img.cjyun.org.cn/a/10695/202404/067ece7dec87d53e26bb9877ae51da87.jpeg",
                "https://img.cjyun.org.cn/a/10695/202404/d21ca8b04b1a2468af5bbbe669ecd2f5.jpeg",
                str(Path("saves/imgs/QQ20251024-172103.png")),
            ]
            
            for query in test_queries:
                logger.info(f"查询: {query}")
                query_embedding = get_image_embedding(query)
                # 执行查询
                results = await self.kb.aquery(
                    query_embeddings=query_embedding,
                    db_id=self.test_db_id,
                    top_k=5,
                    similarity_threshold=0.1
                )
                
                logger.info(f"查询结果数量: {len(results)}")
                
                for i, result in enumerate(results):
                    logger.info(f"  结果 {i+1}:")
                    logger.info(f"    相似度: {result['score']:.4f}")
                    logger.info(f"    元数据: {result['metadata']}")
                    
        except Exception as e:
            logger.error(f"查询图片嵌入失败: {e}")
    async def test_query_documents(self):
        """测试查询文档"""
        logger.info("=== 测试查询文档 ===")
        
        try:
            # 测试博物馆文物相关查询
            test_queries = [
                "玉器文物",
                "战国时期的文物",
                "曾侯乙墓出土的文物",
                "江陵出土的文物",
                "九连墩墓葬文物",
                "玉带钩",
                "水晶串饰",
                "编磬乐器"
            ]
            
            for query in test_queries:
                logger.info(f"查询: {query}")
                
                # 执行查询
                results = await self.kb.aquery(
                    query_text=query,
                    db_id=self.test_db_id,
                    top_k=5,
                    similarity_threshold=0.1
                )
                
                logger.info(f"查询结果数量: {len(results)}")
                
                for i, result in enumerate(results):
                    logger.info(f"  结果 {i+1}:")
                    content = result['content']
                    
                    # 尝试从内容中提取文物信息
                    if '"name"' in content:
                        # 如果是JSON格式的内容，尝试提取name字段
                        import json
                        try:
                            # 查找JSON对象
                            start = content.find('{')
                            end = content.rfind('}') + 1
                            if start != -1 and end != -1:
                                json_str = content[start:end]
                                artifact_data = json.loads(json_str)
                                if 'name' in artifact_data:
                                    logger.info(f"    文物名称: {artifact_data['name']}")
                                if 'description' in artifact_data:
                                    logger.info(f"    文物描述: {artifact_data['description'][:100]}...")
                        except:
                            pass
                    
                    logger.info(f"    内容预览: {content[:150]}...")
                    logger.info(f"    相似度: {result['score']:.4f}")
                    logger.info(f"    元数据: {result['metadata']}")
                
                logger.info("-" * 60)
            
            logger.info("✓ 文物查询测试完成")
            return True
            
        except Exception as e:
            logger.error(f"查询文档失败: {e}")
            return False
    
    async def test_database_operations(self):
        """测试数据库操作"""
        logger.info("=== 测试数据库操作 ===")
        
        try:
            # 测试获取数据库列表
            databases = self.kb.list_databases()
            logger.info(f"数据库列表: {databases}")
            
            # 测试获取数据库信息
            db_info = self.kb.get_database_info(self.test_db_id)
            logger.info(f"数据库信息: {db_info}")
            
            # 测试获取文件列表
            files = self.kb.list_files(self.test_db_id)
            logger.info(f"文件列表: {files}")
            
            logger.info("✓ 数据库操作测试完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库操作失败: {e}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理"""
        logger.info("=== 测试错误处理 ===")
        
        try:
            # 测试查询不存在的数据库
            try:
                await self.kb.aquery("测试查询", "不存在的数据库")
                logger.warning("应该抛出异常但没有")
            except Exception as e:
                logger.info(f"✓ 正确捕获异常: {e}")
            
            # 测试添加文档到不存在的数据库
            try:
                await self.kb.add_content("不存在的数据库", ["test.txt"])
                logger.warning("应该抛出异常但没有")
            except Exception as e:
                logger.info(f"✓ 正确捕获异常: {e}")
            
            logger.info("✓ 错误处理测试完成")
            return True
            
        except Exception as e:
            logger.error(f"错误处理测试失败: {e}")
            return False
    
    async def cleanup(self):
        """清理测试环境"""
        logger.info("=== 清理测试环境 ===")
        
        try:
            # 删除测试数据库
            if self.kb and self.test_db_id in self.kb.databases_meta:
                self.kb.delete_database(self.test_db_id)
                logger.info("✓ 测试数据库已删除")
            
            # 删除临时目录
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info(f"✓ 临时目录已删除: {self.temp_dir}")
            
        except Exception as e:
            logger.error(f"清理失败: {e}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始 ChromaDB 功能测试")
        logger.info("=" * 60)
        
        test_results = []
        
        # 设置测试环境
        if not await self.setup():
            logger.error("测试环境设置失败，终止测试")
            return
        
        # 运行各项测试
        # tests = [
        #     ("创建博物馆文物数据库", self.test_create_database),
        #     ("添加文物文档", self.test_add_documents),
        #     ("添加图片嵌入", self.test_add_image_embeddings),
        #     ("查询文物信息", self.test_query_documents),
        #     ("数据库操作", self.test_database_operations),
        #     ("错误处理", self.test_error_handling),
        # ]
        tests = [
            ("创建博物馆文物数据库", self.test_create_database),
            ("添加图片嵌入", self.test_add_image_embeddings),
            ("查询图片嵌入信息", self.test_query_image_embeddings),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n开始测试: {test_name}")
            try:
                result = await test_func()
                test_results.append((test_name, result))
                if result:
                    logger.info(f"✓ {test_name} 测试通过")
                else:
                    logger.error(f"✗ {test_name} 测试失败")
            except Exception as e:
                logger.error(f"✗ {test_name} 测试异常: {e}")
                test_results.append((test_name, False))
        
        # 清理测试环境
        await self.cleanup()
        
        # 输出测试结果
        logger.info("\n" + "=" * 60)
        logger.info("测试结果汇总:")
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "通过" if result else "失败"
            logger.info(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\n总计: {passed}/{total} 个测试通过")
        
        if passed == total:
            logger.info("🎉 所有测试通过！ChromaDB 功能正常")
        else:
            logger.warning(f"⚠️  有 {total - passed} 个测试失败")


async def main():
    """主函数"""
    tester = ChromaDBTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
