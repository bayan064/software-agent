# software-agent

## 安装配置

### 前置要求

- Python 3.11+
- Java 17+（如需运行 Java 测试）
- DeepSeek API Key（从 https://platform.deepseek.com/ 获取）

### 获取代码

**如果要运行 VSCode 插件或 CLI，需要先下载完整代码：**

```bash
git clone https://github.com/bayan564/software-agent.git
cd software-agent

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
npm run compile
```

### 使用步骤

1. 启动后端：`python server.py`
2. 在 VS Code 中按 `F5` 调试扩展
3. 点击run extension，打开侧边栏的agent-ui图标开始对话
4. 在对话框里输入需求，支持加入附件，编辑对话，复制，查看历史对话等

### 扩展功能

- 多轮对话，支持历史记录
- 流式响应，代码逐字符输出
- 文件上传（.txt, .py, .java 等）
- 一键将代码插入编辑器
- 对话管理（新建/切换/删除）
- 消息编辑和重新生成

---

## Docker 部署

使用 Docker 可以免去手动配置环境的麻烦，在任意支持 Docker 的平台上一键运行智能体服务。

**前置要求**：Docker 已安装并启动 · DeepSeek API Key（从 https://platform.deepseek.com/ 获取）

---

### 场景一：直接拉取镜像运行（无需下载代码）


**1. 获取镜像**

从 Docker Hub 拉取（推荐，需网络）：
```bash
docker pull bayan564/software-agent:latest
```

**2. 启动容器**
```bash
docker run -d -p 8000:8000 --name agent \
  -e DEEPSEEK_API_KEY="你的DeepSeek API密钥" \
  bayan564/software-agent:latest
```

**3. 验证服务**
浏览器访问 `http://localhost:8000/docs`，看到 Swagger 文档页面即表示成功。

---

### 场景二：从源码构建（适合开发者）


**1. 克隆代码**
```bash
git clone https://github.com/bayan564/software-agent.git
cd software-agent
```

**2. 配置 API Key**
```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

**3. 构建并启动**
```bash
docker-compose build
docker-compose up -d
```

**4. 验证服务**
浏览器访问 `http://localhost:8000/docs`，看到 Swagger 文档页面即表示成功。

---

### 镜像信息

本项目镜像已公开推送至 Docker Hub：

| 项目 | 信息 |
|------|------|
| 仓库地址 | https://hub.docker.com/r/bayan564/software-agent |
| 拉取命令 | `docker pull bayan564/software-agent:latest` |
| 镜像大小 | 约 494MB（压缩后） |

### 常用管理命令

| 操作 | 命令 |
|------|------|
| 查看运行状态 | `docker ps` |
| 查看日志 | `docker logs agent` |
| 停止容器 | `docker stop agent` |
| 启动已存在容器 | `docker start agent` |
| 重启容器 | `docker restart agent` |
| 删除容器 | `docker rm agent` |

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| 端口 8000 被占用 | 将 `-p 8000:8000` 改为 `-p 8001:8000`，访问 `http://localhost:8001/docs` |
| 容器启动后立即退出 | 执行 `docker logs agent` 查看错误，通常为 API Key 未配置或无效 |
| Docker Hub 拉取超时 | 使用离线导入方式（场景一步骤1中的方式二） |
| 拉取速度慢 | 配置 Docker 镜像加速器（华为云、阿里云等） |

## 华为云部署

本项目已成功部署至华为云 ECS（Ubuntu 22.04），配置了 systemd 服务实现持久化运行。

**公网访问地址**：`http://120.46.94.151:8000`

**部署架构**：
- 华为云 ECS（2核4GB）
- Python 3.10 + 虚拟环境
- FastAPI + Uvicorn 服务
- systemd 服务守护（开机自启 + 异常重启）

**验证方式**：浏览器访问 `http://120.46.94.151:8000/docs`