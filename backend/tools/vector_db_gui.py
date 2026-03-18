"""向量数据库可视化管理系统（GUI版本）"""
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from typing import List, Dict, Optional

# 添加backend目录到路径
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

from database.vector_db import VectorDatabase
import config


class VectorDBGUI:
    """向量数据库GUI管理界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("向量数据库管理系统")
        self.root.geometry("1200x800")
        
        # 初始化向量数据库
        try:
            self.vector_db = VectorDatabase()
            self.collection = self.vector_db.collection
        except Exception as e:
            messagebox.showerror("错误", f"无法连接向量数据库:\n{e}")
            sys.exit(1)
        
        # 当前数据
        self.all_data = []
        self.filtered_data = []
        
        # 创建界面
        self.create_widgets()
        
        # 加载数据
        self.load_data()
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部工具栏
        toolbar_frame = ttk.Frame(self.root, padding="10")
        toolbar_frame.pack(fill=tk.X)
        
        # 统计信息
        stats_frame = ttk.LabelFrame(toolbar_frame, text="统计信息", padding="10")
        stats_frame.pack(side=tk.LEFT, padx=5)
        
        self.total_label = ttk.Label(stats_frame, text="总记录数: 0", font=("Arial", 10, "bold"))
        self.total_label.pack(side=tk.LEFT, padx=10)
        
        self.event_label = ttk.Label(stats_frame, text="事件数: 0", font=("Arial", 10))
        self.event_label.pack(side=tk.LEFT, padx=10)
        
        self.dialogue_label = ttk.Label(stats_frame, text="对话数: 0", font=("Arial", 10))
        self.dialogue_label.pack(side=tk.LEFT, padx=10)
        
        # 按钮组
        button_frame = ttk.Frame(toolbar_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="刷新", command=self.load_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="添加事件", command=self.show_add_event_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="添加对话", command=self.show_add_dialogue_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="重置数据库", command=self.reset_database).pack(side=tk.LEFT, padx=2)
        
        # 搜索和筛选区域
        filter_frame = ttk.LabelFrame(self.root, text="搜索和筛选", padding="10")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_data())
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="角色ID:").pack(side=tk.LEFT, padx=5)
        self.character_filter_var = tk.StringVar()
        self.character_filter = ttk.Combobox(filter_frame, textvariable=self.character_filter_var, 
                                             width=15, state="readonly")
        self.character_filter.pack(side=tk.LEFT, padx=5)
        self.character_filter.bind('<<ComboboxSelected>>', lambda e: self.filter_data())
        
        ttk.Label(filter_frame, text="类型:").pack(side=tk.LEFT, padx=5)
        self.type_filter_var = tk.StringVar()
        type_filter = ttk.Combobox(filter_frame, textvariable=self.type_filter_var,
                                  values=["", "event", "dialogue_round"], width=15, state="readonly")
        type_filter.pack(side=tk.LEFT, padx=5)
        type_filter.bind('<<ComboboxSelected>>', lambda e: self.filter_data())
        
        # 主内容区域（表格和详情）
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：数据表格
        table_frame = ttk.LabelFrame(content_frame, text="数据列表", padding="10")
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建表格
        columns = ("选择", "文档ID", "角色ID", "事件ID", "类型", "轮次", "预览")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        # 设置列宽
        self.tree.heading("选择", text="选择")
        self.tree.heading("文档ID", text="文档ID")
        self.tree.heading("角色ID", text="角色ID")
        self.tree.heading("事件ID", text="事件ID")
        self.tree.heading("类型", text="类型")
        self.tree.heading("轮次", text="对话轮次")
        self.tree.heading("预览", text="内容预览")
        
        self.tree.column("选择", width=50)
        self.tree.column("文档ID", width=150)
        self.tree.column("角色ID", width=80)
        self.tree.column("事件ID", width=120)
        self.tree.column("类型", width=100)
        self.tree.column("轮次", width=80)
        self.tree.column("预览", width=300)
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击事件
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
        # 全选复选框
        self.select_all_var = tk.BooleanVar()
        select_all_check = ttk.Checkbutton(table_frame, text="全选", variable=self.select_all_var,
                                          command=self.toggle_select_all)
        select_all_check.grid(row=2, column=0, sticky="w", pady=5)
        
        # 右侧：详情显示
        detail_frame = ttk.LabelFrame(content_frame, text="详细信息", padding="10")
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 详情文本区域
        self.detail_text = scrolledtext.ScrolledText(detail_frame, width=50, height=30, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def load_data(self):
        """加载向量数据库数据"""
        try:
            self.status_bar.config(text="正在加载数据...")
            self.root.update()
            
            # 获取所有数据
            results = self.collection.get()
            
            self.all_data = []
            if results.get('ids'):
                for i, doc_id in enumerate(results['ids']):
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    document = results['documents'][i] if results.get('documents') else ""
                    
                    self.all_data.append({
                        'doc_id': doc_id,
                        'character_id': metadata.get('character_id', 'unknown'),
                        'event_id': metadata.get('event_id', 'unknown'),
                        'type': metadata.get('type', 'event'),
                        'dialogue_round': metadata.get('dialogue_round', None),
                        'metadata': metadata,
                        'document': document
                    })
            
            self.filtered_data = self.all_data.copy()
            self.update_stats()
            self.update_character_filter()
            self.update_table()
            
            self.status_bar.config(text=f"加载完成，共 {len(self.all_data)} 条记录")
        except Exception as e:
            messagebox.showerror("错误", f"加载数据失败:\n{e}")
            self.status_bar.config(text="加载失败")
    
    def update_stats(self):
        """更新统计信息"""
        total = len(self.all_data)
        events = sum(1 for item in self.all_data if item['type'] != 'dialogue_round')
        dialogues = sum(1 for item in self.all_data if item['type'] == 'dialogue_round')
        
        self.total_label.config(text=f"总记录数: {total}")
        self.event_label.config(text=f"事件数: {events}")
        self.dialogue_label.config(text=f"对话数: {dialogues}")
    
    def update_character_filter(self):
        """更新角色筛选下拉框"""
        character_ids = sorted(set(item['character_id'] for item in self.all_data))
        self.character_filter['values'] = [''] + character_ids
    
    def filter_data(self):
        """筛选数据"""
        search_term = self.search_var.get().lower()
        character_filter = self.character_filter_var.get()
        type_filter = self.type_filter_var.get()
        
        self.filtered_data = []
        for item in self.all_data:
            match_search = not search_term or \
                search_term in item['doc_id'].lower() or \
                search_term in item['event_id'].lower() or \
                search_term in item['document'].lower()
            
            match_character = not character_filter or item['character_id'] == character_filter
            match_type = not type_filter or item['type'] == type_filter
            
            if match_search and match_character and match_type:
                self.filtered_data.append(item)
        
        self.update_table()
    
    def update_table(self):
        """更新表格显示"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加数据
        for item in self.filtered_data:
            preview = item['document'][:50] + "..." if len(item['document']) > 50 else item['document']
            type_text = "对话轮次" if item['type'] == 'dialogue_round' else "完整事件"
            round_text = item['dialogue_round'] if item['dialogue_round'] else "-"
            
            self.tree.insert("", tk.END, values=(
                "",  # 选择列（通过tag实现）
                item['doc_id'],
                item['character_id'],
                item['event_id'],
                type_text,
                round_text,
                preview
            ), tags=(item['doc_id'],))
    
    def toggle_select_all(self):
        """全选/取消全选"""
        # 这里简化处理，实际可以通过tag来实现复选框效果
        pass
    
    def on_item_double_click(self, event):
        """双击项目显示详情"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        doc_id = item['values'][1]  # 文档ID
        
        # 查找对应的数据
        data_item = next((d for d in self.all_data if d['doc_id'] == doc_id), None)
        if not data_item:
            return
        
        # 显示详情
        detail = f"""文档ID: {data_item['doc_id']}

角色ID: {data_item['character_id']}
事件ID: {data_item['event_id']}
类型: {'对话轮次' if data_item['type'] == 'dialogue_round' else '完整事件'}
对话轮次: {data_item['dialogue_round'] or 'N/A'}

元数据:
{json.dumps(data_item['metadata'], ensure_ascii=False, indent=2)}

完整内容:
{data_item['document']}
"""
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, detail)
    
    def delete_selected(self):
        """删除选中的项目"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的项目")
            return
        
        doc_ids = [self.tree.item(item)['values'][1] for item in selection]
        
        if not messagebox.askyesno("确认", f"确定要删除选中的 {len(doc_ids)} 条记录吗？"):
            return
        
        try:
            self.collection.delete(ids=doc_ids)
            messagebox.showinfo("成功", f"已删除 {len(doc_ids)} 条记录")
            self.load_data()
        except Exception as e:
            messagebox.showerror("错误", f"删除失败:\n{e}")
    
    def reset_database(self):
        """重置数据库"""
        if not messagebox.askyesno("警告", "确定要重置向量数据库吗？\n这将删除所有数据！"):
            return
        
        if not messagebox.askyesno("再次确认", "再次确认：这将永久删除所有数据，无法恢复！"):
            return
        
        try:
            self.vector_db._reset_database()
            self.vector_db.__init__()
            messagebox.showinfo("成功", "数据库已重置")
            self.load_data()
        except Exception as e:
            messagebox.showerror("错误", f"重置失败:\n{e}")
    
    def show_add_event_dialog(self):
        """显示添加事件对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加事件")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 表单字段
        ttk.Label(dialog, text="角色ID:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        character_id_entry = ttk.Entry(dialog, width=30)
        character_id_entry.grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="事件ID:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        event_id_entry = ttk.Entry(dialog, width=30)
        event_id_entry.grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="故事文本:").grid(row=2, column=0, padx=10, pady=5, sticky="nw")
        story_text = scrolledtext.ScrolledText(dialog, width=50, height=8)
        story_text.grid(row=2, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="对话文本:").grid(row=3, column=0, padx=10, pady=5, sticky="nw")
        dialogue_text = scrolledtext.ScrolledText(dialog, width=50, height=8)
        dialogue_text.grid(row=3, column=1, padx=10, pady=5)
        
        def save():
            try:
                self.vector_db.add_event(
                    character_id=int(character_id_entry.get()),
                    event_id=event_id_entry.get(),
                    story_text=story_text.get(1.0, tk.END).strip(),
                    dialogue_text=dialogue_text.get(1.0, tk.END).strip()
                )
                messagebox.showinfo("成功", "事件已添加")
                dialog.destroy()
                self.load_data()
            except Exception as e:
                messagebox.showerror("错误", f"添加失败:\n{e}")
        
        ttk.Button(dialog, text="保存", command=save).grid(row=4, column=1, padx=10, pady=10, sticky="e")
        ttk.Button(dialog, text="取消", command=dialog.destroy).grid(row=4, column=1, padx=10, pady=10, sticky="w")
    
    def show_add_dialogue_dialog(self):
        """显示添加对话对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加对话轮次")
        dialog.geometry("600x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 表单字段
        ttk.Label(dialog, text="角色ID:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        character_id_entry = ttk.Entry(dialog, width=30)
        character_id_entry.grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="事件ID:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        event_id_entry = ttk.Entry(dialog, width=30)
        event_id_entry.grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="故事背景:").grid(row=2, column=0, padx=10, pady=5, sticky="nw")
        story_bg = scrolledtext.ScrolledText(dialog, width=50, height=6)
        story_bg.grid(row=2, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="对话轮次:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        round_entry = ttk.Entry(dialog, width=30)
        round_entry.grid(row=3, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="角色对话:").grid(row=4, column=0, padx=10, pady=5, sticky="nw")
        char_dialogue = scrolledtext.ScrolledText(dialog, width=50, height=6)
        char_dialogue.grid(row=4, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="玩家选择:").grid(row=5, column=0, padx=10, pady=5, sticky="nw")
        player_choice = scrolledtext.ScrolledText(dialog, width=50, height=6)
        player_choice.grid(row=5, column=1, padx=10, pady=5)
        
        def save():
            try:
                self.vector_db.add_dialogue_round(
                    character_id=int(character_id_entry.get()),
                    event_id=event_id_entry.get(),
                    story_background=story_bg.get(1.0, tk.END).strip(),
                    dialogue_round=int(round_entry.get()),
                    character_dialogue=char_dialogue.get(1.0, tk.END).strip(),
                    player_choice=player_choice.get(1.0, tk.END).strip()
                )
                messagebox.showinfo("成功", "对话轮次已添加")
                dialog.destroy()
                self.load_data()
            except Exception as e:
                messagebox.showerror("错误", f"添加失败:\n{e}")
        
        ttk.Button(dialog, text="保存", command=save).grid(row=6, column=1, padx=10, pady=10, sticky="e")
        ttk.Button(dialog, text="取消", command=dialog.destroy).grid(row=6, column=1, padx=10, pady=10, sticky="w")


def main():
    """主函数"""
    root = tk.Tk()
    app = VectorDBGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

