"""
Chroma 向量数据库浏览器（Gradio UI）
用于本地查看和检索 Chroma 向量数据库内容
"""
import gradio as gr
import chromadb
from chromadb.config import Settings
import pandas as pd
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

# 禁用ChromaDB遥测
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['CHROMA_TELEMETRY_DISABLED'] = '1'


class ChromaAuditor:
    """Chroma 数据库审计工具"""
    
    def __init__(self, db_path: Optional[str] = None):
        """初始化
        
        Args:
            db_path: 数据库路径，如果不提供则使用config中的路径
        """
        self.db_path = db_path or config.VECTOR_DB_PATH
        self.client = None
        self.collections = {}
        
    def connect(self) -> bool:
        """连接到数据库"""
        try:
            if not os.path.exists(self.db_path):
                return False
            
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def get_collections(self) -> List[str]:
        """获取所有Collection名称"""
        if not self.client:
            return []
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            print(f"获取Collection列表失败: {e}")
            return []
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取Collection信息"""
        if not self.client:
            return {}
        
        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            
            # 获取一些示例数据
            results = collection.get(limit=min(5, count))
            
            return {
                "name": collection_name,
                "count": count,
                "metadata": collection.metadata or {},
                "sample_ids": results.get('ids', [])[:5],
                "sample_documents": results.get('documents', [])[:5],
                "sample_metadatas": results.get('metadatas', [])[:5]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def search_collection(
        self, 
        collection_name: str, 
        query_text: str, 
        n_results: int = 5
    ) -> Dict[str, Any]:
        """在Collection中搜索"""
        if not self.client:
            return {"error": "未连接到数据库"}
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # 执行搜索
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            # 格式化结果
            formatted_results = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i] if results['documents'] else "",
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None
                    })
            
            return {
                "query": query_text,
                "results": formatted_results,
                "count": len(formatted_results)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_data(self, collection_name: str, limit: int = 100) -> pd.DataFrame:
        """获取Collection中的所有数据（限制数量）"""
        if not self.client:
            return pd.DataFrame()
        
        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            actual_limit = min(limit, count)
            
            results = collection.get(limit=actual_limit)
            
            # 转换为DataFrame
            data = {
                "id": results.get('ids', []),
                "document": results.get('documents', []),
                "metadata": [json.dumps(m, ensure_ascii=False) if m else "" for m in results.get('metadatas', [])]
            }
            
            return pd.DataFrame(data)
        except Exception as e:
            print(f"获取数据失败: {e}")
            return pd.DataFrame()


# 创建全局实例
auditor = ChromaAuditor()


def load_collections():
    """加载Collection列表"""
    if auditor.connect():
        collections = auditor.get_collections()
        if collections:
            return gr.update(choices=collections, value=collections[0] if collections else None)
        else:
            return gr.update(choices=["无Collection"], value=None)
    else:
        return gr.update(choices=["连接失败"], value=None)


def show_collection_info(collection_name: str):
    """显示Collection信息"""
    if not collection_name or collection_name == "无Collection" or collection_name == "连接失败":
        return "请先选择一个Collection", ""
    
    info = auditor.get_collection_info(collection_name)
    
    if "error" in info:
        return f"错误: {info['error']}", ""
    
    # 格式化信息
    info_text = f"""
**Collection名称**: {info['name']}
**记录数量**: {info['count']}
**元数据**: {json.dumps(info.get('metadata', {}), ensure_ascii=False, indent=2)}
"""
    
    # 示例数据
    sample_text = "**示例数据（前5条）**:\n\n"
    for i, (doc_id, doc, metadata) in enumerate(zip(
        info.get('sample_ids', []),
        info.get('sample_documents', []),
        info.get('sample_metadatas', [])
    )):
        sample_text += f"**记录 {i+1}**:\n"
        sample_text += f"- ID: {doc_id}\n"
        sample_text += f"- 内容: {doc[:200]}...\n" if len(doc) > 200 else f"- 内容: {doc}\n"
        sample_text += f"- 元数据: {json.dumps(metadata, ensure_ascii=False)}\n\n"
    
    return info_text, sample_text


def search_in_collection(collection_name: str, query: str, n_results: int):
    """在Collection中搜索"""
    if not collection_name or collection_name == "无Collection" or collection_name == "连接失败":
        return "请先选择一个Collection"
    
    if not query.strip():
        return "请输入搜索查询"
    
    results = auditor.search_collection(collection_name, query, n_results)
    
    if "error" in results:
        return f"搜索失败: {results['error']}"
    
    # 格式化结果
    output = f"**搜索查询**: {results['query']}\n"
    output += f"**找到 {results['count']} 条结果**:\n\n"
    
    for i, result in enumerate(results['results'], 1):
        output += f"**结果 {i}**:\n"
        output += f"- ID: {result['id']}\n"
        output += f"- 相似度距离: {result['distance']:.4f}\n" if result['distance'] is not None else ""
        output += f"- 内容: {result['document']}\n"
        output += f"- 元数据: {json.dumps(result['metadata'], ensure_ascii=False, indent=2)}\n\n"
    
    return output


def view_all_data(collection_name: str, limit: int):
    """查看所有数据"""
    if not collection_name or collection_name == "无Collection" or collection_name == "连接失败":
        return pd.DataFrame()
    
    df = auditor.get_all_data(collection_name, limit)
    return df


# 创建Gradio界面
def create_ui():
    """创建Gradio UI"""
    
    with gr.Blocks(title="Chroma 向量数据库浏览器", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔍 Chroma 向量数据库浏览器")
        gr.Markdown(f"**数据库路径**: `{auditor.db_path}`")
        
        with gr.Row():
            with gr.Column(scale=1):
                collection_dropdown = gr.Dropdown(
                    label="选择 Collection",
                    choices=[],
                    interactive=True
                )
                refresh_btn = gr.Button("🔄 刷新Collection列表", variant="secondary")
            
            with gr.Column(scale=2):
                collection_info = gr.Markdown("请选择一个Collection查看信息")
                sample_data = gr.Markdown("")
        
        with gr.Tabs():
            with gr.Tab("📊 Collection信息"):
                info_btn = gr.Button("查看Collection信息", variant="primary")
                info_btn.click(
                    fn=show_collection_info,
                    inputs=[collection_dropdown],
                    outputs=[collection_info, sample_data]
                )
            
            with gr.Tab("🔍 向量搜索"):
                with gr.Row():
                    search_query = gr.Textbox(
                        label="搜索查询",
                        placeholder="输入要搜索的文本...",
                        lines=2
                    )
                    n_results = gr.Slider(
                        label="返回结果数量",
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1
                    )
                search_btn = gr.Button("🔍 搜索", variant="primary")
                search_results = gr.Markdown("")
                
                search_btn.click(
                    fn=search_in_collection,
                    inputs=[collection_dropdown, search_query, n_results],
                    outputs=[search_results]
                )
            
            with gr.Tab("📋 查看所有数据"):
                data_limit = gr.Slider(
                    label="显示记录数量",
                    minimum=10,
                    maximum=1000,
                    value=100,
                    step=10
                )
                view_btn = gr.Button("📋 查看数据", variant="primary")
                data_table = gr.Dataframe(
                    label="数据表格",
                    wrap=True,
                    height=500
                )
                
                view_btn.click(
                    fn=view_all_data,
                    inputs=[collection_dropdown, data_limit],
                    outputs=[data_table]
                )
        
        # 初始化：加载Collection列表
        refresh_btn.click(
            fn=load_collections,
            outputs=[collection_dropdown]
        )
        
        # 页面加载时自动刷新
        demo.load(
            fn=load_collections,
            outputs=[collection_dropdown]
        )
    
    return demo


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chroma 向量数据库浏览器")
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Chroma数据库路径（默认使用config.VECTOR_DB_PATH）"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="服务器地址（默认: 127.0.0.1）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="服务器端口（默认: 7860）"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="创建公共链接（通过Gradio Share）"
    )
    
    args = parser.parse_args()
    
    # 设置数据库路径
    if args.db:
        auditor.db_path = args.db
    
    # 检查数据库路径
    if not os.path.exists(auditor.db_path):
        print(f"❌ 错误: 数据库路径不存在: {auditor.db_path}")
        print(f"   请检查路径是否正确，或先初始化数据库")
        return
    
    print(f"📂 数据库路径: {os.path.abspath(auditor.db_path)}")
    
    # 创建UI
    demo = create_ui()
    
    # 启动服务器
    print(f"🚀 启动Gradio服务器...")
    print(f"   访问地址: http://{args.host}:{args.port}")
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share
    )


if __name__ == "__main__":
    main()
