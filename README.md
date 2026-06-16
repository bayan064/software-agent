# software-agent

## 安装配置

### 前置要求

- Python 3.11+
- Java 17+（如需运行 Java 测试）
- DeepSeek API Key（从 https://platform.deepseek.com/ 获取）

### 安装步骤

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 验证环境
python check_java_env.py
```

---

## CLI 命令

### 基本用法

```bash
python main.py --input <需求文件路径> [选项]
```

### 参数说明

| 参数 | 必填 | 说明 | 可选值 |
|-----|------|------|--------|
| `--input` | ✅ | 需求文件路径 (.txt) 或 UML 目录 | 文件路径/目录路径 |
| `--output` | ❌ | 输出目录 | 默认 `./output` |
| `--task` | ❌ | 任务类型 | `design`, `code`, `fix`, `full` |
| `--language` | ❌ | 编程语言 | `Python`, `Java` |

### 任务类型

| 任务 | 说明 |
|-----|------|
| `design` | 仅生成设计模型（类图、活动图） |
| `code` | 仅生成代码和测试 |
| `fix` | 独立自愈修复 |
| `full` | 完整流程（设计→编码→测试→修复） |

### 命令示例

```bash
# 完整流程
python main.py --input tests/requirements/req_largest_rectangle.txt --task full --language Python

# 仅生成设计
python main.py --input tests/requirements/req_valid_parentheses.txt --task design

# 从设计文档生成代码
python main.py --input ./output/your_project --task code --language Java

# 修复现有代码
python main.py --input ./output/your_project --task fix --language Python
```

### 输出文件

```
output/
├── solution.py / Solution.java   # 实现代码
├── test_solution.py / TestSolution.java  # 单元测试
├── class_diagram.puml            # 类图（design/full 模式）
├── activity_diagram.puml         # 活动图（design/full 模式）
├── system_design.md              # 设计说明（design/full 模式）
└── error_report.md               # 错误分析报告（fix 模式）
```

---

## IDE 集成

本项目在 [extension](extension) 目录下提供了 VS Code 扩展，注册了调用本地 Agent API 的命令，支持快捷键和编辑器右键菜单。

### 扩展安装编译

```bash
cd extension
npm install
npx tsc
```

### 使用步骤

1. 启动后端：`python server.py`
2. 在 VS Code 中按 `F5` 调试扩展
3. 打开侧边栏开始对话
4. 运行命令 `agent-ui: 生成代码`（或 `Ctrl+Alt+G`）

### 扩展功能

- 多轮对话，支持历史记录
- 流式响应，代码逐字符输出
- 文件上传（.txt, .py, .java 等）
- 一键将代码插入编辑器
- 对话管理（新建/切换/删除）
- 消息编辑和重新生成

---

## Docker 部署

### 快速启动

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 2. 构建并启动
docker-compose build
docker-compose up -d

# 3. 验证
# 浏览器访问 http://localhost:8000/docs
```

### 常用命令

```bash
docker-compose up -d      # 后台启动
docker-compose logs -f    # 查看日志
docker-compose down       # 停止服务
docker-compose restart    # 重启服务
```

---

## 常见问题

| 问题 | 解决方案 |
|-----|---------|
| `No module named 'openai'` | `pip install openai>=1.3.0` |
| API Key 无效 | 检查 `.env` 中的 `DEEPSEEK_API_KEY` |
| Java 测试失败 | 安装 Java 17: `sudo apt install openjdk-17-jdk` |
| 扩展编译失败 | `cd extension && npm install && npx tsc` |
| Docker 启动失败 | `docker-compose logs -f` 查看日志 |
| 端口 8000 被占用 | 修改 `server.py` 或 `docker-compose.yml` 中的端口 |
```