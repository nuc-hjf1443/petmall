# PetMall 宠物综合服务平台

这是一个从 0 开始搭建的宠物综合服务平台初始项目架子，目标是为后续团队协作开发提供统一的前后端目录、文档、部署模板和基础依赖。

当前后端已完成用户基础能力，以及 B 同学负责的商品、购物车、订单支付、
社区和私人知识库/RAG 基础闭环；其他人员负责的宠物档案、Agent、领养和后台仍在开发。

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

知识库 worker 独立启动：

```powershell
cd backend
python -m workers.knowledge_worker
```

订单支付通过 `PETMALL_PAYMENT_MODE=mock|alipay_sandbox` 切换。支付宝沙箱模式必须配置
应用 ID、RSA2 私钥、支付宝公钥、通知地址和回跳地址；真实密钥只允许放入本地 `.env`。

## 前端本地启动

使用 HBuilderX 打开 `frontend/` 目录，运行到 Chrome、Android 或小程序开发工具。

用户端采用一套 Vue 3 + uni-app 页面：小于 `900px` 使用手机单列布局和底部导航，
桌面端使用顶部导航、居中容器和多栏布局。当前已提供首页、登录、商城、购物车、
宠物档案、AI 问答、社区、领养和我的页面。

H5 本地开发默认请求 `http://127.0.0.1:8000`。如需连接其他环境，在
`frontend/` 下从 `.env.example` 创建本地 `.env`，设置：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

生产 H5 未设置该变量时默认请求同域 `/api`，由 `deploy/nginx.conf` 反向代理。
Android 真机不能通过 `127.0.0.1` 访问电脑，请将变量改为开发机局域网地址。

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
- Alembic `0001`—`0005` 迁移
- 部署模板
- 基础依赖清单
- 开发设计文档
- 用户鉴权、地址、商品、SKU、评价和购物车
- 跨商家拆单、库存事务、mock/支付宝沙箱支付
- 社区动态、媒体、互动、关注和举报服务
- 私人知识库上传、RabbitMQ worker、Ollama/ChromaDB 检索
- README、AGENTS 和环境变量模板

待完成：

- 管理员初始化脚本
- 宠物档案、宠物详细资料、领养等业务模块
- AI 导购 Agent、养宠知识问答 Agent
- A 同学宠物资料生成、返币适配器真实接入
- 商品详情、确认订单、订单详情等二级页面的完整交互

## 开发顺序

1. 用户系统、配置加载、数据库会话和鉴权依赖。
2. 宠物档案、用户及宠物详细资料、资料完整度。
3. 智能体与 RAG：导购 Agent、问答 Agent、知识库上传和向量化。
4. 商城、购物车、订单、支付结果。
5. 社区、宠物币、领养和后台审核。
