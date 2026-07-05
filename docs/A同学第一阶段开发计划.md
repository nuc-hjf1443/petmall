# A 同学第一阶段开发计划

## 1. 阶段目标

第一阶段目标是完成 A 同学主导的后端公共基础能力和用户体系基础闭环，让 B/C 能基于统一的数据库会话、鉴权依赖、用户模型和地址能力继续并行开发。

本阶段只覆盖：

- 配置加载。
- 异步数据库会话。
- JWT 鉴权与 `token_version`。
- 阿里云号码认证服务短信验证码。
- 用户注册、登录、退出、刷新 Token。
- 当前用户资料读取与更新。
- 修改密码后旧 Token 失效。
- 收货地址管理。
- A 侧第一批 Alembic 迁移。
- 第一阶段相关测试。

本阶段不覆盖宠物档案、成长记录、提醒、宠物币、导购 Agent。这些属于后续阶段。

## 2. 依据文档

- `docs/后端三人分工开发计划.md`
  - 第 1 阶段：基础骨架和公共能力。
  - 第 1 周人员 A：完成用户、鉴权、用户资料、地址基础接口；完成数据库会话、JWT、依赖注入。
  - 人员 A 模块一：用户注册登录。
  - 人员 A 模块二：地址管理。
- `docs/宠物商城开发设计文档.md`
  - 4.1 用户与权限。
  - 5.1 基础表中的用户相关表。
  - 5.2 `user` 关键字段建议。
  - 6.1 通用接口规范。
  - 6.2 认证典型接口。
- `E:\AISource\项目开发\secondProject\发送短信开发.pdf`
  - 使用阿里云“号码认证服务（短信认证）”免资质测试通道。
  - 使用专属 SDK `alibabacloud_dypnsapi20170525`。
  - 网关 endpoint 固定为 `dypnsapi.aliyuncs.com`。
  - 测试模板 `TemplateCode` 固定为 `100001`。
  - 模板参数必须包含 `code` 和 `min`，并序列化为 JSON 字符串。
  - 手机号需要先在阿里云控制台测试号码中绑定，未绑定号码无法收到测试短信。

## 3. 交付范围

### 3.1 公共基础能力

新增或完善以下能力：

- `backend/settings/config.py`
  - 统一读取 `PETMALL_` 前缀环境变量。
  - 支持从 `backend/.env` 读取本地配置。
  - 暴露数据库、Redis、JWT、CORS、文件目录等配置。
- `backend/models/base.py`
  - 定义 SQLAlchemy `Base`。
  - 统一表命名与基础模型约定。
- `backend/models/database.py`
  - 创建 async engine。
  - 创建 `async_sessionmaker`。
  - 提供数据库 session 工厂。
- `backend/core/auth.py`
  - 密码哈希与校验，使用 Argon2。
  - JWT 生成与解析。
  - Access Token 中写入 `sub`、`token_version`、`type`、`exp`。
- `backend/core/dependencies.py`
  - `get_db`。
  - `get_current_user`。
  - `require_admin`。
  - `require_merchant`。
- `backend/core/cache.py`
  - 封装 Redis client。
  - 支持验证码写入、读取和删除。
- `backend/services/sms_service.py`
  - 封装阿里云号码认证服务短信验证码发送。
  - 本地生成 6 位数字验证码。
  - 调用 `SendSmsVerifyCodeRequest`。
  - 成功后只把验证码交给业务服务写入 Redis，不直接返回给正式客户端。
- `backend/core/errors.py`
  - 统一业务错误码和异常。
- `backend/core/response.py`
  - 统一响应结构。
- `backend/main.py`
  - 注册 CORS。
  - 注册静态资源目录。
  - 注册 `auth_router` 和 `user_router`。

### 3.2 用户体系

新增用户注册、登录、资料和密码能力：

- `backend/models/user.py`
- `backend/schemas/user_schema.py`
- `backend/schemas/auth_schema.py`
- `backend/repository/user_repository.py`
- `backend/services/auth_service.py`
- `backend/services/user_service.py`
- `backend/services/sms_service.py`
- `backend/routers/auth_router.py`
- `backend/routers/user_router.py`

核心接口：

```http
POST /auth/code
POST /auth/register
POST /auth/login
POST /auth/logout
POST /auth/refresh
GET  /users/me
PUT  /users/me/profile
POST /users/me/change-password
```

关键行为：

- 注册使用 `phone + password`，`email` 可选。
- 手机验证码作为注册校验项；本地开发可通过配置开启 debug 返回验证码，正式环境不得返回验证码。
- 手机号唯一，邮箱如果填写也应唯一。
- 手机号格式按中国大陆手机号校验：`^1[3-9]\d{9}$`。
- 密码必须哈希存储，不能明文落库。
- 登录支持手机号或邮箱。
- 冻结用户、软删除用户不能登录。
- 修改密码后递增 `token_version`，旧 Token 失效。
- `logout` 第一阶段采用无状态退出，由前端清理 Token，不引入 Token blacklist 表。
- 用户资料接口只能读写当前登录用户自己的资料。

短信验证码行为：

- `POST /auth/code` 接收手机号并发送验证码。
- 使用阿里云“号码认证服务（短信认证）”，不是标准阿里云短信服务。
- SDK 使用 `alibabacloud_dypnsapi20170525`。
- 网关 endpoint 使用 `dypnsapi.aliyuncs.com`。
- `sign_name` 必须与阿里云控制台体验测试页面完全一致。
- `template_code` 第一阶段使用测试模板 `100001`。
- 模板参数：

```json
{"code": "123456", "min": "5"}
```

- `template_param` 传给 SDK 前必须 `json.dumps`。
- 验证码由后端生成 6 位随机数字。
- 验证码写入 Redis，key 建议为 `sms:code:{phone}`，过期时间 300 秒。
- 同一手机号 60 秒内不允许重复发送，限流 key 建议为 `sms:cooldown:{phone}`。
- 注册成功或验证码校验成功后删除 `sms:code:{phone}`。
- 阿里云返回 `OK` 才视为发送成功。
- SDK 异常、云端拒绝、手机号未绑定测试号码都返回明确错误，不吞异常。

### 3.3 地址管理

新增地址管理能力：

- `user_address` 表。
- 当前用户地址增删改查。
- 默认地址设置。
- 给 B 的订单模块预留地址快照服务方法。

核心接口：

```http
GET    /users/me/addresses
POST   /users/me/addresses
PUT    /users/me/addresses/{address_id}
DELETE /users/me/addresses/{address_id}
POST   /users/me/addresses/{address_id}/default
```

关键行为：

- 用户只能管理自己的地址。
- 每个用户最多只有一个默认地址。
- 新增第一条地址时自动设为默认地址。
- 设置某个地址为默认时，同一用户其他地址自动取消默认。
- 删除默认地址后，自动把最近更新的一条未删除地址设为默认。
- 没有剩余地址时，不设置默认地址。
- 删除地址采用软删除。
- 预留服务方法：

```python
async def get_address_snapshot(user_id: int, address_id: int) -> dict
```

该方法给 B 创建订单时读取完整收货地址快照使用。

## 4. 数据模型

### 4.1 `user`

建议字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 用户 ID |
| `phone` | 手机号，唯一 |
| `email` | 邮箱，可空，唯一 |
| `nickname` | 昵称 |
| `avatar` | 头像 URL |
| `city` | 城市 |
| `password_hash` | 密码哈希 |
| `is_admin` | 是否管理员 |
| `is_merchant` | 是否商家 |
| `is_frozen` | 是否冻结 |
| `is_deleted` | 是否软删除 |
| `token_version` | Token 版本 |
| `real_name_status` | 实名状态 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### 4.2 `user_profile`

建议字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 资料 ID |
| `user_id` | 用户 ID |
| `pet_experience` | 养宠经验 |
| `living_city` | 所在城市 |
| `living_environment` | 居住环境 |
| `budget_preference` | 预算偏好 |
| `preferred_categories` | 常购品类 |
| `feeding_philosophy` | 喂养理念 |
| `allergy_notes` | 过敏或禁忌备注 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### 4.3 `user_address`

建议字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 地址 ID |
| `user_id` | 用户 ID |
| `receiver_name` | 收货人 |
| `receiver_phone` | 收货手机号 |
| `province` | 省 |
| `city` | 市 |
| `district` | 区县 |
| `detail_address` | 详细地址 |
| `postal_code` | 邮编，可空 |
| `is_default` | 是否默认地址 |
| `is_deleted` | 是否软删除 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

## 5. Alembic 迁移

第一批 A 侧迁移只创建以下表：

- `user`
- `user_profile`
- `user_address`

不提前创建商品、商家、领养、宠物档案、宠物币、Agent、知识库等表，避免越过 B/C 分工边界。

需要补齐：

- Alembic 配置文件。
- `backend/alembic/env.py`。
- `backend/alembic/script.py.mako`。
- `backend/alembic/versions/0001_user_auth_profile_address.py`。

## 6. 环境变量

不修改 `backend/.env`，只维护 `backend/.env.example`。

需要确保模板中包含：

```env
PETMALL_MYSQL_DB_URI=mysql+aiomysql://root:change_me@127.0.0.1:3306/petmall?charset=utf8mb4
PETMALL_REDIS_URL=redis://127.0.0.1:6379/0
PETMALL_RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5672/
PETMALL_JWT_SECRET_KEY=change_me_in_local_env
PETMALL_JWT_ALGORITHM=HS256
PETMALL_ACCESS_TOKEN_EXPIRE_MINUTES=1440
PETMALL_GENERATED_ASSET_DIR=generated
PETMALL_VECTOR_STORE_DIR=generated/vector_store
PETMALL_PAYMENT_MODE=mock
PETMALL_MOCK_PAYMENT_ENABLED=true
```

真实密钥、Token、证书、生产数据库地址不得写入代码、文档或测试数据。

短信相关配置：

```env
PETMALL_ALIYUN_SMS_ACCESS_KEY_ID=
PETMALL_ALIYUN_SMS_ACCESS_KEY_SECRET=
PETMALL_ALIYUN_SMS_SIGN_NAME=
PETMALL_ALIYUN_SMS_TEMPLATE_CODE=100001
PETMALL_ALIYUN_SMS_ENDPOINT=dypnsapi.aliyuncs.com
PETMALL_SMS_CODE_EXPIRE_SECONDS=300
PETMALL_SMS_SEND_COOLDOWN_SECONDS=60
PETMALL_SMS_DEBUG_CODE_ENABLED=false
```

依赖需要补充到 `backend/requirements.txt`：

```text
alibabacloud_dypnsapi20170525
```

说明：

- `PETMALL_ALIYUN_SMS_ACCESS_KEY_ID` 和 `PETMALL_ALIYUN_SMS_ACCESS_KEY_SECRET` 只能放在本地或部署环境变量中。
- `PETMALL_SMS_DEBUG_CODE_ENABLED=true` 只允许本地联调使用，正式环境必须为 `false`。
- 阿里云免资质测试通道需要在控制台绑定测试手机号，最多支持绑定 5 个测试号码。

## 7. 测试计划

新增测试放在 `backend/tests/`。

必须覆盖：

- 注册成功。
- 发送短信验证码成功。
- 未绑定测试手机号或云端拒绝时返回失败。
- 手机号格式错误时不发送短信。
- 同一手机号 60 秒内重复发送失败。
- 验证码写入 Redis，300 秒后过期。
- 验证码错误或过期时注册失败。
- 手机号重复注册失败。
- 登录成功。
- 密码错误登录失败。
- 冻结用户登录失败。
- 软删除用户登录失败。
- 获取当前用户资料。
- 更新当前用户资料。
- 修改密码后旧 Token 失效。
- 新密码可登录。
- 新增地址。
- 获取地址列表。
- 更新地址。
- 删除地址。
- 设置默认地址。
- 同一用户默认地址唯一。
- 删除默认地址后自动处理默认状态。
- 越权操作他人地址失败。

建议验证命令：

```powershell
.\.venv\Scripts\python.exe -m compileall backend
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

## 8. 验收标准

完成后应满足：

- 后端能启动，`/docs` 可查看新增接口。
- 可通过 `POST /auth/code` 发送手机号验证码。
- 验证码只存入 Redis，正式响应不返回明文验证码。
- 用户可注册、登录、刷新 Token、退出。
- 密码全程哈希存储。
- 冻结和软删除用户不能登录。
- 修改密码后旧 Token 失效。
- 当前用户可读取和更新自己的资料。
- 用户可维护多个地址。
- 每个用户只有一个默认地址。
- B 创建订单时可以通过服务方法读取地址快照。
- A 侧第一批 Alembic 迁移可执行。
- 第一阶段测试通过。

## 9. 边界说明

本阶段不做以下内容：

- 宠物档案。
- 宠物详细资料。
- 成长记录。
- 基础提醒。
- 宠物币账户、签到、任务、流水。
- AI 宠物用品导购 Agent。
- 商品、购物车、订单、支付。
- 商家、领养、后台审核。
- 私人知识库和 RAG 入库。

这些能力按三人分工计划在后续阶段由对应人员继续实现。
