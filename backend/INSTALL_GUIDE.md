# 后端依赖安装完整指南

## 问题说明

当前存在依赖冲突：
- **ChromaDB 0.4.22** 需要 `numpy < 2.0`
- **rembg 2.0.72** 需要 `numpy >= 2.3.0`

这两个要求无法同时满足，需要调整版本。

## 解决方案

### 方案一：使用兼容的 rembg 版本（推荐）

使用支持 numpy 1.x 的 rembg 版本。

---

## 完整安装流程

### 步骤1: 激活虚拟环境

```powershell
# 进入后端目录
cd d:\Develop\Project\NoEndStory\backend

# 激活虚拟环境
.\venv\Scripts\Activate.ps1
```

如果遇到 PowerShell 执行策略错误，运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 步骤2: 卸载冲突的包

```powershell
# 卸载当前版本的 numpy 和 rembg
pip uninstall numpy rembg -y
```

### 步骤3: 安装兼容的 numpy 版本

```powershell
# 安装 numpy 1.26.4（兼容 ChromaDB 和旧版 rembg）
pip install "numpy==1.26.4"
```

### 步骤4: 安装兼容的 rembg 版本

**重要**：rembg 2.0.30 及之前的版本不支持 Python 3.11（需要 Python < 3.11）。

对于 Python 3.11，需要尝试 2.0.41 到 2.0.49 之间的版本：

```powershell
# 首先尝试 2.0.41（最早支持 Python 3.11 的版本）
pip install "rembg==2.0.41"
```

如果 2.0.41 要求 numpy 2.x，尝试稍新的版本：
```powershell
# 尝试 2.0.45
pip install "rembg==2.0.45"
```

或者：
```powershell
# 尝试 2.0.49（最后一个可能支持 numpy 1.x 的版本）
pip install "rembg==2.0.49"
```

**如果所有版本都要求 numpy 2.x**，请查看下面的"方案三：使用替代方案"。

### 步骤5: 安装其他依赖

```powershell
# 从 requirements.txt 安装其他依赖（跳过已安装的）
pip install -r requirements.txt
```

或者逐个安装：

```powershell
# 数据库相关
pip install "psycopg2-binary==2.9.9"
pip install "sqlalchemy==2.0.23"
pip install "pgvector==0.2.4"

# 向量数据库
pip install "chromadb==0.4.22"

# 环境配置
pip install "python-dotenv==1.0.0"

# AI 相关
pip install "openai==1.12.0"
pip install "dashscope>=1.17.0"
pip install "sentence-transformers>=2.2.0"

# Web 框架
pip install "fastapi>=0.104.0"
pip install "uvicorn[standard]>=0.24.0"
pip install "pydantic>=2.0.0"
pip install "python-multipart>=0.0.6"

# 图片处理
pip install "Pillow>=10.0.0"

# HTTP 请求
pip install "requests>=2.31.0"
```

### 步骤6: 验证安装

```powershell
# 检查 numpy 版本
python -c "import numpy; print('NumPy version:', numpy.__version__)"
# 应该输出: NumPy version: 1.26.4

# 检查 rembg 版本
python -c "import rembg; print('rembg version:', rembg.__version__)"
# 应该输出 rembg 版本号

# 检查 ChromaDB 是否可以导入
python -c "import chromadb; print('ChromaDB version:', chromadb.__version__)"
# 应该输出: ChromaDB version: 0.4.22

# 测试 rembg 是否可以初始化会话
python -c "from rembg import new_session; session = new_session('isnet-general-use'); print('rembg session created successfully')"
```

### 步骤7: 测试后端启动

```powershell
# 尝试启动后端
python .\run_api.py
```

如果启动成功，应该看到：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 如果方案一不工作，使用方案二

### 方案二：升级 ChromaDB（如果可用）

检查是否有支持 numpy 2.0 的 ChromaDB 版本：

```powershell
# 查看最新的 ChromaDB 版本
pip index versions chromadb

# 如果最新版本支持 numpy 2.0，可以尝试：
pip uninstall chromadb numpy -y
pip install "numpy>=2.3.0"
pip install "chromadb>=0.5.0"  # 或最新版本
pip install "rembg>=2.0.50"
```

**注意**：根据搜索结果，ChromaDB 目前还不完全支持 numpy 2.0，所以方案一更可靠。

---

## 如果方案一和方案二都不工作，使用方案三

### 方案三：使用替代的背景去除方案

如果 rembg 的所有 Python 3.11 兼容版本都要求 numpy 2.x，可以考虑：

#### 选项A：使用 PIL/Pillow 的简单背景去除（已实现）

代码中已经有基于 PIL 的白色背景去除功能（在 `image_service.py` 的 `composite_scene_with_character` 方法中），可以暂时使用这个方案。

#### 选项B：升级 ChromaDB 到最新版本（如果支持 numpy 2.0）

```powershell
# 检查最新 ChromaDB 版本
pip index versions chromadb

# 如果最新版本支持 numpy 2.0，可以尝试：
pip uninstall chromadb numpy rembg -y
pip install "numpy>=2.3.0"
pip install "chromadb>=0.5.0"  # 或最新版本
pip install "rembg>=2.0.50"
```

#### 选项C：降级 Python 到 3.10（不推荐）

如果必须使用 rembg 2.0.30，可以考虑使用 Python 3.10：
```powershell
# 创建新的虚拟环境（Python 3.10）
python3.10 -m venv venv310
.\venv310\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 更新 requirements.txt（可选）

如果方案一成功，可以更新 `requirements.txt` 以固定兼容版本：

```txt
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pgvector==0.2.4
chromadb==0.4.22
python-dotenv==1.0.0
numpy==1.26.4  # 固定版本，避免冲突
openai==1.12.0
dashscope>=1.17.0
sentence-transformers>=2.2.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6
Pillow>=10.0.0
requests>=2.31.0
rembg==2.0.30  # 使用兼容 numpy 1.x 的版本
```

---

## 常见问题

### Q1: 安装 rembg 时提示需要 numpy >= 2.3.0

**A**: 使用 rembg 2.0.30 或更早的版本：
```powershell
pip install "rembg==2.0.30"
```

### Q2: ChromaDB 导入失败，提示 np.float_ 错误

**A**: 确保 numpy 版本 < 2.0：
```powershell
pip install "numpy==1.26.4"
```

### Q3: rembg 模型下载失败

**A**: rembg 首次使用时会自动下载模型（约 200MB），确保网络连接正常。如果下载失败，可以手动下载：
- 模型会保存在 `~/.u2net/` 目录（Windows: `C:\Users\<用户名>\.u2net\`）

### Q4: 虚拟环境激活失败

**A**: PowerShell 执行策略问题，运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 完整安装命令（一键执行）

```powershell
# 进入后端目录
cd d:\Develop\Project\NoEndStory\backend

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 卸载冲突包
pip uninstall numpy rembg -y

# 安装兼容版本（使用约束文件防止升级）
pip install "numpy==1.26.4" "rembg==2.0.41" -c constraints.txt

# 安装其他依赖（使用约束文件）
pip install -r requirements.txt -c constraints.txt

# 验证安装
python -c "import numpy; import rembg; import chromadb; print('所有依赖安装成功！')"
```

## 如果在新终端中遇到 numpy 2.x 问题

如果在新终端中启动后端时遇到 `np.float_` 错误，运行修复脚本：

```powershell
cd d:\Develop\Project\NoEndStory\backend
.\venv\Scripts\Activate.ps1
.\fix_numpy.ps1
```

或者手动修复：
```powershell
pip uninstall numpy -y
pip install "numpy==1.26.4" --force-reinstall --no-deps
```

---

## 验证清单

安装完成后，确认以下内容：

- [ ] numpy 版本为 1.26.4
- [ ] rembg 可以导入
- [ ] ChromaDB 可以导入
- [ ] rembg 可以创建会话（`new_session('isnet-general-use')`）
- [ ] 后端可以正常启动（`python run_api.py`）

如果所有项目都打勾，说明安装成功！
