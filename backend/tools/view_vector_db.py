"""查看向量数据库内容的脚本"""
import sys
import os
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

from database.vector_db import VectorDatabase
import json

def view_vector_db(character_id=None):
    """查看向量数据库内容
    
    Args:
        character_id: 可选，如果提供则只显示该角色的数据
    """
    print("=" * 80)
    print("向量数据库内容查看")
    print("=" * 80)
    
    try:
        # 初始化向量数据库
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 获取所有数据
        if character_id:
            # 只获取特定角色的数据
            results = collection.get(
                where={"character_id": str(character_id)}
            )
            print(f"\n[筛选] 只显示角色ID {character_id} 的数据")
        else:
            # 获取所有数据
            results = collection.get()
            print(f"\n[全部数据] 显示所有角色的数据")
        
        # 检查是否有数据
        if not results.get('ids') or len(results['ids']) == 0:
            print("\n向量数据库中暂无数据")
            return
        
        print(f"\n总记录数: {len(results['ids'])}\n")
        print("=" * 80)
        
        # 按角色ID分组显示
        character_groups = {}
        for i, doc_id in enumerate(results['ids']):
            metadata = results['metadatas'][i] if results.get('metadatas') else {}
            document = results['documents'][i] if results.get('documents') else ""
            
            char_id = metadata.get('character_id', 'unknown')
            event_id = metadata.get('event_id', 'unknown')
            event_type = metadata.get('type', 'event')  # 'event' 或 'dialogue_round'
            
            if char_id not in character_groups:
                character_groups[char_id] = []
            
            character_groups[char_id].append({
                'doc_id': doc_id,
                'event_id': event_id,
                'type': event_type,
                'metadata': metadata,
                'document': document
            })
        
        # 显示每个角色的数据
        for char_id, events in character_groups.items():
            print(f"\n{'=' * 80}")
            print(f"角色ID: {char_id}")
            print(f"事件数量: {len(events)}")
            print(f"{'=' * 80}")
            
            # 按类型分组
            complete_events = [e for e in events if e['type'] == 'complete_event' or e['type'] == 'event']
            dialogue_rounds = [e for e in events if e['type'] == 'dialogue_round']
            
            if complete_events:
                print(f"\n【完整事件】({len(complete_events)}个):")
                for event in complete_events:
                    print(f"\n  - 文档ID: {event['doc_id']}")
                    print(f"    事件ID: {event['event_id']}")
                    print(f"    元数据: {json.dumps(event['metadata'], ensure_ascii=False, indent=6)}")
                    doc_preview = event['document'][:200] + "..." if len(event['document']) > 200 else event['document']
                    print(f"    内容预览: {doc_preview}")
            
            if dialogue_rounds:
                print(f"\n【对话轮次】({len(dialogue_rounds)}个):")
                for dialogue in dialogue_rounds[:10]:  # 只显示前10个
                    print(f"\n  - 文档ID: {dialogue['doc_id']}")
                    print(f"    事件ID: {dialogue['event_id']}")
                    print(f"    对话轮次: {dialogue['metadata'].get('dialogue_round', 'unknown')}")
                    doc_preview = dialogue['document'][:150] + "..." if len(dialogue['document']) > 150 else dialogue['document']
                    print(f"    内容预览: {doc_preview}")
                
                if len(dialogue_rounds) > 10:
                    print(f"\n    ... 还有 {len(dialogue_rounds) - 10} 个对话轮次未显示")
        
        print(f"\n{'=' * 80}")
        print("查看完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[错误] 查看向量数据库失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 如果提供了命令行参数，则只显示该角色的数据
    character_id = None
    if len(sys.argv) > 1:
        try:
            character_id = int(sys.argv[1])
        except ValueError:
            print(f"[错误] 无效的角色ID: {sys.argv[1]}")
            print("用法: python view_vector_db.py [角色ID]")
            sys.exit(1)
    
    view_vector_db(character_id)

