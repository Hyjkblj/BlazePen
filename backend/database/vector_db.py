"""向量数据库管理（使用ChromaDB）。

注意：该模块会被剧情/角色链路间接 import。为了让 training-only 与单元测试在缺少
onnxruntime 等重依赖时仍可启动/导入，我们将 ChromaDB/embedding 的导入延迟到
VectorDatabase 实例化阶段。
"""

import config
import os
import shutil
import warnings
import time
import gc

# 禁用ChromaDB遥测（通过环境变量）
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['CHROMA_TELEMETRY_DISABLED'] = '1'

# 设置Hugging Face镜像站（用于下载embedding模型）
if 'HF_ENDPOINT' not in os.environ:
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 忽略ChromaDB的遥测警告
warnings.filterwarnings('ignore', category=UserWarning, module='chromadb')
warnings.filterwarnings('ignore', message='.*telemetry.*')
warnings.filterwarnings('ignore', message='.*capture.*')


class VectorDatabase:
    """向量数据库管理器"""
    
    def __init__(self):
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings  # type: ignore
            from chromadb.utils import embedding_functions  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                "ChromaDB dependencies are not available. Install optional dependencies (e.g. chromadb, onnxruntime) "
                "or disable vector DB features."
            ) from exc

        # Store references for later methods to use without re-import.
        self._chromadb = chromadb
        self._Settings = Settings
        self._embedding_functions = embedding_functions

        os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)
        
        # 获取embedding函数
        self.embedding_function = self._get_embedding_function()
        
        # 尝试创建客户端，如果失败则重置数据库
        try:
            # 禁用遥测功能，避免telemetry错误
            self.client = self._chromadb.PersistentClient(
                path=config.VECTOR_DB_PATH,
                settings=self._Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            # 尝试获取或创建集合（使用自定义embedding函数）
            self.collection = self.client.get_or_create_collection(
                name="story_events",
                embedding_function=self.embedding_function,
                metadata={"description": "存储剧情事件内容", "embedding_model": config.EMBEDDING_MODEL}
            )
        except Exception as e:
            # 如果出现数据库兼容性问题，删除旧数据库并重新创建
            print(f"[警告] 向量数据库初始化失败: {e}")
            print("[信息] 正在重置向量数据库...")
            
            # 先关闭可能存在的客户端连接
            try:
                if hasattr(self, 'client'):
                    del self.client
            except:
                pass
            
            # 强制垃圾回收，释放文件句柄
            gc.collect()
            time.sleep(0.5)
            
            # 重置数据库
            self._reset_database()
            
            # 等待文件系统操作完成
            time.sleep(0.5)
            
            # 重新初始化
            try:
                self.client = self._chromadb.PersistentClient(
                    path=config.VECTOR_DB_PATH,
                    settings=self._Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                self.collection = self.client.get_or_create_collection(
                    name="story_events",
                    embedding_function=self.embedding_function,
                    metadata={"description": "存储剧情事件内容", "embedding_model": config.EMBEDDING_MODEL}
                )
                print(f"[信息] 向量数据库已重置，使用embedding模型: {config.EMBEDDING_MODEL}")
            except Exception as e2:
                print(f"[错误] 重新初始化失败: {e2}")
                print(f"[提示] 请关闭所有Python进程，然后手动删除目录: {config.VECTOR_DB_PATH}")
                print(f"[提示] 或者运行修复脚本: python fix_vector_db.py")
                raise
    
    def _get_embedding_function(self):
        """根据配置获取embedding函数"""
        model_name = config.EMBEDDING_MODEL.lower()
        
        if model_name == 'default':
            # ChromaDB默认模型（all-MiniLM-L6-v2）
            return self._embedding_functions.DefaultEmbeddingFunction()
        elif model_name == 'text2vec-chinese':
            # 中文优化模型（推荐）
            try:
                return self._embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="shibing624/text2vec-base-chinese"
                )
            except Exception as e:
                print(f"[警告] 无法加载text2vec-chinese模型: {e}")
                print("[提示] 正在安装依赖: pip install sentence-transformers")
                print("[信息] 回退到默认模型")
                return self._embedding_functions.DefaultEmbeddingFunction()
        elif model_name == 'm3e-base':
            # M3E中文embedding模型
            try:
                return self._embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="moka-ai/m3e-base"
                )
            except Exception as e:
                print(f"[警告] 无法加载m3e-base模型: {e}")
                print("[提示] 正在安装依赖: pip install sentence-transformers")
                print("[信息] 回退到默认模型")
                return self._embedding_functions.DefaultEmbeddingFunction()
        elif model_name == 'bge-small-zh-v1.5':
            # 百度开源中文embedding模型
            try:
                return self._embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="BAAI/bge-small-zh-v1.5"
                )
            except Exception as e:
                print(f"[警告] 无法加载bge-small-zh-v1.5模型: {e}")
                print("[提示] 正在安装依赖: pip install sentence-transformers")
                print("[信息] 回退到默认模型")
                return self._embedding_functions.DefaultEmbeddingFunction()
        elif model_name == 'paraphrase-multilingual':
            # 多语言模型（支持中英文）
            try:
                return self._embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                )
            except Exception as e:
                print(f"[警告] 无法加载paraphrase-multilingual模型: {e}")
                print("[提示] 正在安装依赖: pip install sentence-transformers")
                print("[信息] 回退到默认模型")
                return self._embedding_functions.DefaultEmbeddingFunction()
        else:
            print(f"[警告] 未知的embedding模型: {model_name}，使用默认模型")
            return self._embedding_functions.DefaultEmbeddingFunction()
    
    def _reset_database(self):
        """重置向量数据库（删除旧数据）- 改进的Windows文件锁定处理"""
        max_retries = 5
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                if os.path.exists(config.VECTOR_DB_PATH):
                    # Windows下需要特殊处理SQLite文件锁定
                    sqlite_file = os.path.join(config.VECTOR_DB_PATH, 'chroma.sqlite3')
                    if os.path.exists(sqlite_file):
                        try:
                            # 先尝试删除SQLite文件
                            os.remove(sqlite_file)
                            time.sleep(0.2)
                        except PermissionError:
                            # 如果删除失败，尝试重命名（避免锁定）
                            try:
                                backup_name = sqlite_file + f".old_{int(time.time())}"
                                os.rename(sqlite_file, backup_name)
                                print(f"[信息] SQLite文件被占用，已重命名为: {backup_name}")
                            except:
                                pass
                    
                    # 删除整个目录
                    try:
                        shutil.rmtree(config.VECTOR_DB_PATH, ignore_errors=True)
                        time.sleep(0.3)
                    except:
                        pass
                    
                    # 重新创建目录
                    os.makedirs(config.VECTOR_DB_PATH, exist_ok=True)
                    return  # 成功删除，退出循环
                    
            except PermissionError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[警告] 文件被占用，等待 {wait_time:.1f} 秒后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"[错误] 重置数据库失败: {e}")
                    print(f"[提示] 请关闭所有Python进程，然后手动删除目录: {config.VECTOR_DB_PATH}")
                    print(f"[提示] 或者运行修复脚本: python fix_vector_db.py")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[警告] 重置失败，等待 {wait_time:.1f} 秒后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"[错误] 重置数据库失败: {e}")
                    raise
    
    def add_event(self, character_id: int, event_id: str, story_text: str, 
                  dialogue_text: str, metadata: dict = None):
        """添加事件到向量数据库"""
        # 组合故事文本和对话文本作为文档内容
        content = f"{story_text}\n\n{dialogue_text}"
        
        # 创建唯一ID
        doc_id = f"{character_id}_{event_id}"
        
        # 检查是否已存在（避免重复添加）
        try:
            existing = self.collection.get(ids=[doc_id])
            if existing['ids'] and len(existing['ids']) > 0:
                print(f"[向量数据库] 事件已存在，跳过保存: {doc_id}")
                return  # 已存在，跳过保存
        except Exception as e:
            # 查询失败不影响保存流程
            print(f"[向量数据库] 检查已存在记录时出错（继续保存）: {e}")
        
        # 准备元数据
        event_metadata = {
            'character_id': str(character_id),
            'event_id': event_id,
            **{k: str(v) for k, v in (metadata or {}).items()}
        }
        
        # 添加到集合（捕获遥测错误，不影响功能）
        try:
            self.collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[event_metadata]
            )
            print(f"[向量数据库] 事件保存成功: {doc_id}")
        except Exception as e:
            # 如果是遥测相关错误，忽略它
            if 'telemetry' in str(e).lower() or 'capture' in str(e).lower():
                # 遥测错误不影响功能，可以忽略
                print(f"[向量数据库] 遥测错误（可忽略）: {e}")
            elif 'existing embedding ID' in str(e).lower() or 'already exists' in str(e).lower():
                # 重复添加警告，可以忽略（已在上面检查，但可能并发导致）
                print(f"[向量数据库] 事件已存在（并发情况）: {doc_id}")
            else:
                # 其他错误需要抛出
                print(f"[向量数据库] 保存事件失败: {e}")
                raise
    
    def search_similar_events(self, character_id: int, query: str, n_results: int = 3):
        """搜索相似的历史事件"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"character_id": str(character_id)}
            )
            
            # 确保返回格式一致
            if not results.get('ids') or len(results['ids']) == 0:
                return {'ids': [], 'documents': [], 'metadatas': []}
            
            return results
        except Exception as e:
            # 如果查询失败（比如没有数据），返回空结果
            return {'ids': [], 'documents': [], 'metadatas': []}
    
    def get_event_by_id(self, character_id: int, event_id: str):
        """根据ID获取事件"""
        doc_id = f"{character_id}_{event_id}"
        results = self.collection.get(ids=[doc_id])
        
        if results['ids']:
            return {
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        return None
    
    def add_dialogue_round(self, character_id: int, event_id: str, story_background: str,
                          dialogue_round: int, character_dialogue: str, player_choice: str,
                          metadata: dict = None, states: object = None, state_changes: dict = None):
        """添加单轮对话到向量数据库（重构版：支持四类文本存储）
        
        Args:
            character_id: 角色ID（与PostgreSQL关联的key）
            event_id: 事件ID
            story_background: 故事背景（原始文本，会进行概括）
            dialogue_round: 对话轮次
            character_dialogue: 角色对话（原封不动存储，但会加上状态值）
            player_choice: 玩家选择（原封不动存储，但会加上状态值影响）
            metadata: 额外元数据
            states: 角色状态对象（CharacterState）
            state_changes: 玩家选项带来的状态值变化字典
        """
        from game.emotion_utils import (
            get_emotion_tags, 
            get_all_states_text, 
            get_state_changes_text,
            summarize_story_background
        )
        
        # 1. 概括故事背景文本（在什么时间、什么地点、玩家和角色做了什么）
        summarized_background = summarize_story_background(story_background)
        
        # 2. 角色文本 + 所有12个状态值
        states_text = get_all_states_text(states) if states else "状态值未知"
        character_text_with_states = f"{character_dialogue}\n[角色状态：{states_text}]"
        
        # 3. 玩家选项文本 + 状态值影响
        state_changes_text = get_state_changes_text(state_changes) if state_changes else "无状态变化"
        player_choice_with_impact = f"{player_choice}\n[状态影响：{state_changes_text}]"
        
        # 4. 情绪状态标签（用于向量化）
        emotion_tags = get_emotion_tags(states) if states else "情绪状态未知"
        
        # 组合四类文本（用于向量化检索）
        content = f"""
[故事背景概括]：{summarized_background}

[角色文本]：{character_text_with_states}

[玩家选项]：{player_choice_with_impact}

[情绪状态]：{emotion_tags}
""".strip()
        
        # 创建唯一ID（包含轮次）
        doc_id = f"{character_id}_{event_id}_round_{dialogue_round}"
        
        # 检查是否已存在（避免重复添加）
        try:
            existing = self.collection.get(ids=[doc_id])
            if existing['ids'] and len(existing['ids']) > 0:
                print(f"[向量数据库] 对话轮次已存在，跳过保存: {doc_id}")
                return  # 已存在，跳过保存
        except Exception as e:
            # 查询失败不影响保存流程
            print(f"[向量数据库] 检查已存在记录时出错（继续保存）: {e}")
        
        # 准备元数据（混合方案：metadata存储精确值用于过滤）
        dialogue_metadata = {
            'character_id': str(character_id),
            'event_id': event_id,
            'dialogue_round': str(dialogue_round),
            'type': 'dialogue_round',
        }
        
        # 添加情绪相关字段到metadata（用于精确过滤）
        if states:
            dialogue_metadata.update({
                'emotion': str(states.emotion),
                'favorability': str(states.favorability),
                'trust': str(states.trust),
                'hostility': str(states.hostility),
                'dependence': str(states.dependence),
                'stress': str(states.stress),
                'anxiety': str(states.anxiety),
                'happiness': str(states.happiness),
                'sadness': str(states.sadness),
                'confidence': str(states.confidence),
                'initiative': str(states.initiative),
                'caution': str(states.caution),
                'emotion_level': 'high' if states.emotion >= 70 else 'medium' if states.emotion >= 40 else 'low',
            })
        
        # 添加其他元数据
        if metadata:
            dialogue_metadata.update({k: str(v) for k, v in metadata.items()})
        
        # 添加到集合（捕获遥测错误，不影响功能）
        try:
            self.collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[dialogue_metadata]
            )
            print(f"[向量数据库] 对话轮次保存成功: {doc_id}")
        except Exception as e:
            # 如果是遥测相关错误，忽略它
            if 'telemetry' in str(e).lower() or 'capture' in str(e).lower():
                # 遥测错误不影响功能，可以忽略
                print(f"[向量数据库] 遥测错误（可忽略）: {e}")
            elif 'existing embedding ID' in str(e).lower() or 'already exists' in str(e).lower():
                # 重复添加警告，可以忽略（已在上面检查，但可能并发导致）
                print(f"[向量数据库] 对话轮次已存在（并发情况）: {doc_id}")
            else:
                # 其他错误需要抛出
                print(f"[向量数据库] 保存对话轮次失败: {e}")
                raise
    
    def search_recent_dialogues(self, character_id: int, event_id: str = None, n_results: int = 5):
        """搜索最近的对话内容（用于生成下一轮对话）
        
        Args:
            character_id: 角色ID
            event_id: 事件ID（可选，如果提供则只搜索该事件的对话）
            n_results: 返回结果数量
        """
        try:
            # 构建查询条件
            where_clause = {
                'character_id': str(character_id),
                'type': 'dialogue_round'
            }
            if event_id:
                where_clause['event_id'] = event_id
            
            # 搜索最近的对话
            results = self.collection.query(
                query_texts=["对话 剧情 发展"],
                n_results=n_results,
                where=where_clause
            )
            
            # 确保返回格式一致
            if not results.get('ids') or len(results['ids']) == 0:
                return {'ids': [], 'documents': [], 'metadatas': []}
            
            return results
        except Exception as e:
            # 如果查询失败，返回空结果
            return {'ids': [], 'documents': [], 'metadatas': []}

