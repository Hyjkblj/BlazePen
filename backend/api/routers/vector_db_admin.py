"""向量数据库管理API路由"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict
from api.response import success_response, error_response
from database.vector_db import VectorDatabase
from pydantic import BaseModel

router = APIRouter(prefix="/v1/admin/vector-db", tags=["向量数据库管理"])


class AddEventRequest(BaseModel):
    """添加事件请求"""
    character_id: int
    event_id: str
    story_text: str
    dialogue_text: str
    metadata: Optional[Dict] = None


class AddDialogueRequest(BaseModel):
    """添加对话轮次请求"""
    character_id: int
    event_id: str
    story_background: str
    dialogue_round: int
    character_dialogue: str
    player_choice: str
    metadata: Optional[Dict] = None


class DeleteRequest(BaseModel):
    """删除请求"""
    doc_ids: List[str]  # 文档ID列表


@router.get("/list")
async def list_all_data(character_id: Optional[int] = None):
    """获取所有向量数据库数据"""
    try:
        import config
        import os
        import logging
        logger = logging.getLogger(__name__)
        
        # 调试：打印向量数据库路径和工作目录
        logger.info(f"当前工作目录: {os.getcwd()}")
        logger.info(f"向量数据库路径: {config.VECTOR_DB_PATH}")
        logger.info(f"路径是否存在: {os.path.exists(config.VECTOR_DB_PATH)}")
        
        # 检查chroma.sqlite3文件
        chroma_db_file = os.path.join(config.VECTOR_DB_PATH, 'chroma.sqlite3')
        logger.info(f"chroma.sqlite3路径: {chroma_db_file}")
        logger.info(f"chroma.sqlite3是否存在: {os.path.exists(chroma_db_file)}")
        
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 调试：打印集合信息和所有集合
        logger.info(f"集合名称: {collection.name}")
        logger.info(f"集合数量: {collection.count()}")
        
        # 列出所有集合
        try:
            all_collections = vector_db.client.list_collections()
            logger.info(f"所有集合: {[c.name for c in all_collections]}")
            for col in all_collections:
                logger.info(f"  集合 '{col.name}': {col.count()} 条记录")
        except Exception as e:
            logger.warning(f"无法列出所有集合: {e}")
        
        # 获取所有数据
        if character_id:
            results = collection.get(where={"character_id": str(character_id)})
        else:
            results = collection.get()
        
        # 调试：打印查询结果
        logger.info(f"查询到的记录数: {len(results.get('ids', []))}")
        if results.get('ids'):
            logger.info(f"前3个ID: {results.get('ids', [])[:3]}")
        
        # 组织数据
        data_list = []
        if results.get('ids'):
            for i, doc_id in enumerate(results['ids']):
                metadata = results['metadatas'][i] if results.get('metadatas') else {}
                document = results['documents'][i] if results.get('documents') else ""
                
                data_list.append({
                    'doc_id': doc_id,
                    'character_id': metadata.get('character_id', 'unknown'),
                    'event_id': metadata.get('event_id', 'unknown'),
                    'type': metadata.get('type', 'event'),
                    'dialogue_round': metadata.get('dialogue_round', None),
                    'metadata': metadata,
                    'document': document,
                    'document_preview': document[:200] + "..." if len(document) > 200 else document
                })
        
        # 按角色ID分组统计
        character_stats = {}
        for item in data_list:
            char_id = item['character_id']
            if char_id not in character_stats:
                character_stats[char_id] = {
                    'total': 0,
                    'events': 0,
                    'dialogues': 0
                }
            character_stats[char_id]['total'] += 1
            if item['type'] == 'dialogue_round':
                character_stats[char_id]['dialogues'] += 1
            else:
                character_stats[char_id]['events'] += 1
        
        return success_response(data={
            'total': len(data_list),
            'character_stats': character_stats,
            'items': data_list
        })
    except Exception as e:
        return error_response(code=500, message=f"获取数据失败: {str(e)}")


@router.post("/add-event")
async def add_event(request: AddEventRequest):
    """添加事件到向量数据库"""
    try:
        vector_db = VectorDatabase()
        vector_db.add_event(
            character_id=request.character_id,
            event_id=request.event_id,
            story_text=request.story_text,
            dialogue_text=request.dialogue_text,
            metadata=request.metadata
        )
        return success_response(data={"message": "事件添加成功"})
    except Exception as e:
        return error_response(code=500, message=f"添加事件失败: {str(e)}")


@router.post("/add-dialogue")
async def add_dialogue(request: AddDialogueRequest):
    """添加对话轮次到向量数据库"""
    try:
        vector_db = VectorDatabase()
        vector_db.add_dialogue_round(
            character_id=request.character_id,
            event_id=request.event_id,
            story_background=request.story_background,
            dialogue_round=request.dialogue_round,
            character_dialogue=request.character_dialogue,
            player_choice=request.player_choice,
            metadata=request.metadata
        )
        return success_response(data={"message": "对话轮次添加成功"})
    except Exception as e:
        return error_response(code=500, message=f"添加对话轮次失败: {str(e)}")


@router.post("/delete")
async def delete_data(request: DeleteRequest):
    """删除向量数据库中的数据"""
    try:
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 删除指定的文档
        collection.delete(ids=request.doc_ids)
        
        return success_response(data={
            "message": f"成功删除 {len(request.doc_ids)} 条数据",
            "deleted_count": len(request.doc_ids)
        })
    except Exception as e:
        return error_response(code=500, message=f"删除数据失败: {str(e)}")


@router.delete("/delete-by-character/{character_id}")
async def delete_by_character(character_id: int):
    """删除指定角色的所有数据"""
    try:
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 获取该角色的所有数据
        results = collection.get(where={"character_id": str(character_id)})
        
        if not results.get('ids'):
            return success_response(data={"message": "该角色没有数据", "deleted_count": 0})
        
        # 删除所有数据
        collection.delete(ids=results['ids'])
        
        return success_response(data={
            "message": f"成功删除角色 {character_id} 的所有数据",
            "deleted_count": len(results['ids'])
        })
    except Exception as e:
        return error_response(code=500, message=f"删除数据失败: {str(e)}")


@router.post("/reset")
async def reset_database():
    """重置向量数据库（危险操作）"""
    try:
        vector_db = VectorDatabase()
        vector_db._reset_database()
        
        # 重新初始化
        vector_db.__init__()
        
        return success_response(data={"message": "向量数据库已重置"})
    except Exception as e:
        return error_response(code=500, message=f"重置数据库失败: {str(e)}")


@router.get("/stats")
async def get_stats():
    """获取向量数据库统计信息"""
    try:
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 获取所有数据
        results = collection.get()
        
        total_count = len(results.get('ids', []))
        
        # 统计各类型数据
        type_stats = {}
        character_stats = {}
        
        if results.get('metadatas'):
            for metadata in results['metadatas']:
                data_type = metadata.get('type', 'event')
                char_id = metadata.get('character_id', 'unknown')
                
                type_stats[data_type] = type_stats.get(data_type, 0) + 1
                character_stats[char_id] = character_stats.get(char_id, 0) + 1
        
        return success_response(data={
            'total': total_count,
            'type_stats': type_stats,
            'character_stats': character_stats
        })
    except Exception as e:
        return error_response(code=500, message=f"获取统计信息失败: {str(e)}")

