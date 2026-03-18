"""检查情绪数据是否存储在向量数据库中"""
import sys
import os
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

from database.vector_db import VectorDatabase
import json

def check_emotion_in_vector_db():
    """检查向量数据库中是否包含情绪数据"""
    print("=" * 80)
    print("检查情绪数据在向量数据库中的存储情况")
    print("=" * 80)
    
    try:
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 获取所有数据
        results = collection.get()
        
        if not results.get('ids'):
            print("\n向量数据库为空，无法检查")
            return
        
        print(f"\n总记录数: {len(results['ids'])}")
        
        # 检查metadata中是否包含情绪相关字段
        emotion_fields = ['emotion', 'favorability', 'trust', 'hostility', 
                         'dependence', 'stress', 'anxiety', 'happiness', 
                         'sadness', 'confidence', 'initiative', 'caution']
        
        all_meta_keys = set()
        for metadata in results.get('metadatas', []):
            all_meta_keys.update(metadata.keys())
        
        print(f"\n向量数据库中所有metadata字段: {sorted(all_meta_keys)}")
        
        # 检查是否包含情绪字段
        found_emotion_fields = [field for field in emotion_fields if field in all_meta_keys]
        
        print(f"\n情绪相关字段检查:")
        print(f"  期望的情绪字段: {emotion_fields}")
        print(f"  实际找到的字段: {found_emotion_fields}")
        
        if found_emotion_fields:
            print(f"\n✓ 找到 {len(found_emotion_fields)} 个情绪相关字段")
            # 显示样本数据
            print("\n样本数据（包含情绪字段的记录）:")
            for i, metadata in enumerate(results.get('metadatas', [])):
                if any(field in metadata for field in emotion_fields):
                    print(f"\n  记录 {i+1}:")
                    print(f"    文档ID: {results['ids'][i]}")
                    emotion_data = {k: v for k, v in metadata.items() if k in emotion_fields}
                    print(f"    情绪数据: {json.dumps(emotion_data, ensure_ascii=False, indent=6)}")
                    if i >= 2:  # 只显示前3条
                        break
        else:
            print(f"\n✗ 未找到任何情绪相关字段！")
            print(f"\n问题分析:")
            print(f"  1. 情绪数据没有被存储到向量数据库的metadata中")
            print(f"  2. 情绪数据没有被包含在documents文本中（未向量化）")
            print(f"  3. 无法通过向量检索来找到相似情绪状态的历史事件")
        
        # 检查documents中是否包含情绪信息
        print(f"\n检查documents文本中是否包含情绪信息:")
        emotion_keywords = ['情绪', 'emotion', '好感度', '信任度', 'favorability', 'trust']
        found_in_docs = 0
        for i, doc in enumerate(results.get('documents', [])):
            if any(keyword in doc.lower() for keyword in emotion_keywords):
                found_in_docs += 1
                if found_in_docs <= 3:
                    print(f"\n  文档 {i+1} 包含情绪关键词:")
                    print(f"    文档ID: {results['ids'][i]}")
                    # 找到包含关键词的片段
                    for keyword in emotion_keywords:
                        if keyword in doc.lower():
                            idx = doc.lower().find(keyword)
                            snippet = doc[max(0, idx-50):min(len(doc), idx+50)]
                            print(f"    片段: ...{snippet}...")
                            break
        
        if found_in_docs == 0:
            print(f"  ✗ documents文本中未找到情绪相关信息")
        else:
            print(f"  ✓ 在 {found_in_docs} 个文档中找到情绪相关信息")
        
        print("\n" + "=" * 80)
        print("检查完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[错误] 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_emotion_in_vector_db()

