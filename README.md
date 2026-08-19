# 中转站管理面板

集中管理多个 **LLM API 中转站**（如 New API 搭建的中转站）的本地 Web 工具：填写中转站**地址**与**密钥**，查看每个中转站有哪些**可用模型**，并对模型逐个**实测**验证是否真正可用。

## 功能特性

- ✅ 多中转站集中管理（新增 / 编辑 / 删除）
- ✅ 同时兼容 **OpenAI 兼容** 与 **Anthropic 兼容** 协议，并支持**自动探测**
- ✅ 一键拉取模型列表（`/v1/models`）
- ✅ 批量 / 单个实测模型（发一条测试消息验证连通性），显示**可用 / 不可用、延迟、错误信息**
- ✅ 密钥只保存在本地后端，前端接口返回时自动**打码**
- ✅ 配置持久化到本地 `data/stations.json`

## 环境要求

- Python 3.9+（本项目在 3.14 上开发验证）
- Windows / macOS / Linux

## 安装

```bash
pip install -r requirements.txt
```

> 若 `pip` 不在 PATH 中，可用 `py -m pip install -r requirements.txt`。

## 启动

**方式一：双击启动**（Windows）

双击 `start.bat`。

**方式二：命令行**

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动后浏览器打开：<http://127.0.0.1:8000>

## 使用说明

1. 点击左侧「＋ 新增」，填写中转站的**名称**、**地址（Base URL）**、**API 密钥**，协议默认「自动探测」。
2. 点击左侧列表选中中转站，右侧点击「**拉取模型**」获取该站可用模型列表。
3. 点击「**测试全部**」批量实测，或对单个模型点「测试」。
4. 结果以 ✅ 可用 / ❌ 不可用展示，并给出延迟与错误信息。

> 关于 Base URL：填写 `https://api.example.com` 或 `https://api.example.com/v1` 均可，系统会自动补齐 `/v1`。

## 项目结构

```
app/
  main.py          # FastAPI 入口
  config.py        # 常量配置
  schemas.py       # Pydantic 数据模型
  storage.py       # 配置读写（JSON）
  adapters.py      # OpenAI / Anthropic 协议适配
  routers/
    stations.py    # 中转站 CRUD + 模型拉取 + 测试 API
static/
  index.html       # 前端页面
  app.js           # 前端逻辑
  style.css        # 样式
data/
  stations.json    # 中转站配置（本地生成，已 git 忽略）
  stations.example.json  # 示例配置
```

## 安全说明

- 中转站密钥保存在本地 `data/stations.json`，该文件已被 `.gitignore` 排除，**不会**提交到 Git。
- 前端接口返回的密钥为打码形式（如 `sk-1******abcd`），真实密钥只在后端持有。

## 常见问题

- **拉取模型返回 401 / 403**：密钥无效或无权限，请检查中转站后台的令牌。
- **连接被重置 / 超时**：中转站地址不可达，或需要配置代理。
- **编辑时不想改密钥**：编辑弹窗中密钥留空即可保持原密钥不变。
