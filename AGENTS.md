# AGENTS.md

## 沟通方式

- 默认中文沟通。
- 代码、命令、变量名、文件路径保持英文。
- 结论先行，表达简洁直接。
- 发现目录、设计或实现不合理时，直接指出并说明原因。

## 项目定位

这是宠物综合服务平台从 0 开始开发的初始架子。

当前重点是保持清晰的工程边界，先让团队能稳定拉取、启动和继续开发，不追求一次性实现完整业务。

V1.0 按 `docs/宠物商城开发设计文档.md` 推进，核心范围包括用户系统、宠物档案、用户及宠物详细资料、商城订单、双模式支付、智能体、私人知识库、RAG、社区、领养、宠物币和后台审核。

## 目录边界

- `backend/`：FastAPI 后端代码。
- `frontend/`：uni-app 前端代码。
- `docs/`：需求、开发设计和项目说明文档。
- `deploy/`：Docker、docker-compose、Nginx 等部署模板。

不要把后端模块散落到仓库根目录。

## 后端分层约定

- `backend/routers/`：HTTP 路由、请求参数、响应模型、鉴权依赖。
- `backend/schemas/`：Pydantic 请求和响应模型。
- `backend/models/`：SQLAlchemy ORM 模型和数据库会话基础配置。
- `backend/repository/`：数据库查询、分页、创建、更新等数据访问逻辑。
- `backend/services/`：跨表业务逻辑和状态流转。
- `backend/core/`：鉴权、密码哈希、JWT、缓存、支付客户端、文件存储、Agent 工作流、RAG 检索和向量化等通用能力。
- `backend/settings/`：配置加载，不在业务代码中硬编码环境配置。
- `backend/scripts/`：管理员创建、初始化数据、维护脚本。
- `backend/tests/`：后端自动化测试。

后端模块命名优先遵循开发文档：

- `auth_router.py`、`user_router.py`、`pet_router.py`
- `product_router.py`、`cart_router.py`、`order_router.py`、`payment_router.py`
- `agent_router.py`、`knowledge_router.py`
- `community_router.py`、`adoption_router.py`、`coin_router.py`
- `merchant_router.py`、`admin_router.py`

## 前端约定

- 使用 `frontend/` 作为 HBuilderX 打开的 uni-app 工程目录。
- 页面放在 `frontend/pages/`。
- 静态资源放在 `frontend/static/`。
- 后续新增接口封装、状态管理、公共组件时，优先放在 `frontend/api/`、`frontend/store/`、`frontend/components/`。
- V1.0 页面优先级：登录、首页、我的、宠物档案、宠物详细资料、智能导购、知识库、商城、购物车、订单、社区、领养。

## 配置与密钥

- 不提交 `backend/.env`。
- 新增环境变量时，同步更新 `backend/.env.example` 和相关文档。
- 不在代码、文档、测试数据中写入真实密码、Token、证书、支付密钥或生产数据库地址。
- 本地生成文件放在 `backend/generated/`，真实生成内容不提交。
- 私人知识库文件、解析文本、向量索引必须按用户隔离；删除用户或文档时，业务实现需要同步清理关联数据。
- `PETMALL_PAYMENT_MODE=mock` 只能用于本地开发、演示和自动化测试，不能作为真实收款链路。

## 依赖与基础设施

- 后端运行依赖至少包括 MySQL、Redis、RabbitMQ。
- 完整 Agent/RAG 能力依赖 DeepSeek API、Ollama、ChromaDB；启用 LangGraph 多轮记忆时还需要 PostgreSQL。
- 新增 Python 依赖必须写入 `backend/requirements.txt`。
- 新增外部服务必须同步更新 `README.md`、`backend/.env.example` 和开发文档。

## 测试约定

- 后端测试放在 `backend/tests/`。
- 重点覆盖鉴权、权限越权、支付回调幂等、Agent 商品防编造、RAG 用户隔离、知识问答医疗风险提示。
- 前端重点覆盖登录态失效、页面跳转、导购 Agent 商品卡片、知识库上传、支付结果页。

## Git 约定

- 不自动 `git commit` 或 `git push`，除非用户明确要求。
- 提交前先展示将要提交的变更摘要。
- commit message 使用简洁英文。
- 不提交 `.venv/`、`.idea/`、`__pycache__/`、`frontend/unpackage/`、`frontend/node_modules/`。

## 红线操作

以下操作必须先确认：

- 删除文件、目录或 Git 历史。
- 修改 `.env`、密钥、Token、证书、CI/CD 配置。
- `git push`、`git rebase`、`git reset --hard`、强制推送。
- 公开发布、生产部署、`npm publish` 等操作。
