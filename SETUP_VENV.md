# 虚拟环境设置指南

## Windows 系统

### 方法一：使用命令行

```bash
# 1. 进入 backend 目录
cd backend

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
venv\Scripts\activate

# 激活成功后，命令行前面会显示 (venv)
```

### 方法二：使用 PowerShell

```powershell
# 1. 进入 backend 目录
cd backend

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境（可能需要设置执行策略）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

---

## 验证虚拟环境

激活虚拟环境后，执行以下命令验证：

```bash
# 查看 Python 路径（应该指向 venv 目录）
python -c "import sys; print(sys.executable)"

# 查看 pip 位置
pip --version
```

---

## 安装依赖

激活虚拟环境后：

```bash
# 升级 pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r backend/requirements.txt
```

---

## 退出虚拟环境

```bash
deactivate
```

---

## 项目结构

创建虚拟环境后，项目结构应该是：

```
backend/
├── venv/              # 虚拟环境目录（新创建）
├── app/
├── requirements.txt
└── ...
```

---

## 注意事项

1. ⚠️ **venv 目录不要提交到 Git**（已在 .gitignore 中配置）
2. ⚠️ **每次开发前都要激活虚拟环境**
3. ⚠️ **确保 Python 版本 >= 3.10**

---

*创建虚拟环境后，可以继续安装依赖和配置环境变量*
