# PetMall 宠物综合服务平台

这是一个从 0 开始搭建的宠物综合服务平台初始项目架子，目标是为后续团队协作开发提供统一的前后端目录、文档、部署模板和基础依赖。

当前阶段只完成工程骨架，不代表业务功能已经实现。

## 产品定位

平台面向宠物主人、准宠物主人、宠物商家、救助机构、宠物服务人员和平台运营人员，V1.0 目标是打通：

- 用户注册登录、资料、地址管理。
- 宠物档案、宠物详细资料、成长记录、健康提醒。
- 宠物商城、购物车、订单、双模式支付。
- AI 宠物用品导购 Agent、养宠知识问答 Agent。
- 私人知识库上传、宠物资料文件生成、RAG 检索增强。
- 宠物社区、领养申请、宠物币积分。
- 商家后台和平台管理后台基础审核能力。

## 技术栈

- 前端：uni-app、Vue 3
- 后端：FastAPI、Uvicorn、SQLAlchemy Async ORM
- 数据库：MySQL 8
- 缓存：Redis
- 消息队列：RabbitMQ、aio-pika
- 迁移：Alembic
- 智能体：LangChain、LangGraph、DeepSeek
- RAG：ChromaDB、Ollama `nomic-embed-text`、PyPDF
- 支付：本地 mock 支付、支付宝沙箱支付
- 部署模板：Docker、docker-compose、Nginx

## 目录结构

```text
petmall/
├── backend/                 FastAPI 后端
│   ├── alembic/             数据库迁移目录占位
│   ├── core/                通用基础能力
│   ├── generated/           本地上传和生成文件目录
│   ├── models/              SQLAlchemy 模型
│   ├── repository/          数据访问层
│   ├── routers/             API 路由
│   ├── schemas/             Pydantic 请求/响应模型
│   ├── scripts/             初始化和维护脚本
│   ├── services/            业务服务层
│   ├── settings/            配置加载
│   ├── tests/               后端测试
│   ├── main.py              FastAPI 入口
│   └── requirements.txt     Python 依赖
├── frontend/                uni-app 前端
└── deploy/                  部署模板
```

## 后端本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
cd backend
python -m uvicorn main:app --reload
```

启动后访问：

- API 根路径：`http://127.0.0.1:8000/`
- FastAPI 文档：`http://127.0.0.1:8000/docs`

完整 Agent/RAG 能力还需要准备 MySQL、Redis、RabbitMQ、Ollama、DeepSeek API。启用 LangGraph 多轮记忆时，还需要 PostgreSQL。

## 前端本地启动

使用 HBuilderX 打开 `frontend/` 目录，运行到 Chrome、Android 或小程序开发工具。

当前前端也只是初始 uni-app 架子，业务页面需要后续开发。

## 环境变量

不要提交 `backend/.env`。

首次启动前复制示例文件：

```powershell
Copy-Item backend\.env.example backend\.env
```

然后按本地 MySQL、Redis、RabbitMQ、JWT、DeepSeek、Ollama、支付模式等环境修改 `backend/.env`。

## Docker 模板

`deploy/` 下已预留开发/测试用模板：

- `deploy/Dockerfile`
- `deploy/docker-compose.yml`
- `deploy/nginx.conf`

这些文件不是生产配置。生产上线前必须补充 HTTPS、域名、CORS 限制、数据库账号、备份策略和密钥管理。

## 当前完成状态

已完成：

- 前后端目录边界
- 后端基础包目录
- 本地生成文件目录占位
- Alembic 迁移目录占位
- 部署模板
- 基础依赖清单
- 开发设计文档
- README、AGENTS 和环境变量模板

待完成：

- 后端配置加载
- 数据库连接和 Alembic 正式初始化
- 用户注册、登录、JWT
- 管理员初始化脚本
- 宠物档案、宠物详细资料、商城、订单、社区、领养等业务模块
- AI 导购 Agent、养宠知识问答 Agent
- 私人知识库、资料文件生成、RAG 检索
- 支付宝沙箱和本地 mock 双模式支付
- 前端业务页面

## 开发顺序

1. 用户系统、配置加载、数据库会话和鉴权依赖。
2. 宠物档案、用户及宠物详细资料、资料完整度。
3. 智能体与 RAG：导购 Agent、问答 Agent、知识库上传和向量化。
4. 商城、购物车、订单、支付结果。
5. 社区、宠物币、领养和后台审核。
