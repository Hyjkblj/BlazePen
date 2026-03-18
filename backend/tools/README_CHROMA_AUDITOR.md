# Chroma 向量数据库浏览器使用指南

## 简介

`chroma_auditor.py` 是一个基于 Gradio 的本地 UI 工具，用于查看和检索 Chroma 向量数据库的内容，无需使用 Cloud 服务。

## 功能特性

✅ **Collection 浏览**: 查看所有 Collection 及其基本信息  
✅ **向量搜索**: 使用文本查询进行相似度搜索  
✅ **数据查看**: 以表格形式查看所有存储的数据  
✅ **元数据查看**: 查看每条记录的元数据信息  
✅ **本地运行**: 完全本地化，无需网络连接（除了下载模型）  

## 安装依赖

```bash
cd backend
pip install gradio pandas
```

或者使用 requirements.txt（已包含）：
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```bash
cd backend
python tools/chroma_auditor.py
```

默认配置：
- 数据库路径：使用 `config.VECTOR_DB_PATH`（默认：`./vector_db`）
- 服务器地址：`http://127.0.0.1:7860`

### 指定数据库路径

```bash
python tools/chroma_auditor.py --db ./vector_db
```

### 自定义服务器地址和端口

```bash
python tools/chroma_auditor.py --host 0.0.0.0 --port 8080
```

### 创建公共链接（通过 Gradio Share）

```bash
python tools/chroma_auditor.py --share
```

注意：公共链接会在 72 小时后过期。

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--db` | Chroma数据库路径 | `config.VECTOR_DB_PATH` |
| `--host` | 服务器地址 | `127.0.0.1` |
| `--port` | 服务器端口 | `7860` |
| `--share` | 创建公共链接 | `False` |

## 界面功能

### 1. Collection 信息

- 显示 Collection 名称、记录数量、元数据
- 显示前 5 条示例数据

### 2. 向量搜索

- 输入文本查询
- 设置返回结果数量（1-20）
- 显示相似度距离、内容、元数据

### 3. 查看所有数据

- 以表格形式显示所有数据
- 可设置显示数量限制（10-1000）
- 包含 ID、文档内容、元数据

## 使用示例

### 示例 1: 查看数据库中的所有 Collection

1. 启动工具：`python tools/chroma_auditor.py`
2. 在浏览器中打开：`http://127.0.0.1:7860`
3. 点击"刷新Collection列表"按钮
4. 选择要查看的 Collection

### 示例 2: 搜索相似内容

1. 选择 Collection
2. 切换到"向量搜索"标签
3. 输入搜索查询（例如："在食堂相遇"）
4. 设置返回结果数量
5. 点击"搜索"按钮

### 示例 3: 查看所有数据

1. 选择 Collection
2. 切换到"查看所有数据"标签
3. 设置显示记录数量
4. 点击"查看数据"按钮

## 注意事项

⚠️ **数据库路径**: 确保指定的数据库路径存在且可访问  
⚠️ **性能**: 如果数据库很大，建议限制查看数量  
⚠️ **编码**: 确保终端支持 UTF-8 编码（Windows 可能需要额外配置）  

## 故障排除

### 问题 1: 连接失败

**错误**: "连接失败" 或 "数据库路径不存在"

**解决方案**:
- 检查数据库路径是否正确
- 确保数据库已初始化（运行 `python scripts/init_chroma.py`）
- 检查路径权限

### 问题 2: 没有 Collection

**错误**: Collection 列表为空

**解决方案**:
- 确保数据库中有数据
- 检查 Collection 名称是否正确
- 尝试重新初始化数据库

### 问题 3: 搜索无结果

**错误**: 搜索返回空结果

**解决方案**:
- 检查查询文本是否正确
- 尝试使用不同的关键词
- 检查 Collection 中是否有数据

## 技术细节

- **框架**: Gradio 4.0+
- **数据库**: ChromaDB 0.4.22
- **数据处理**: Pandas
- **编码**: UTF-8

## 相关文件

- `backend/database/vector_db.py`: 向量数据库管理
- `backend/config.py`: 配置文件（包含 VECTOR_DB_PATH）
- `scripts/init_chroma.py`: 数据库初始化脚本
