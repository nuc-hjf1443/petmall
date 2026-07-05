# A 同学第一阶段交接文档

## 1. 交接结论

A 同学第一阶段后端基础能力已完成：用户注册登录、短信验证码、JWT 鉴权、用户资料、地址管理、数据库会话、Alembic 首个迁移和自动化测试已经落地。

未执行 `git commit`、未执行 `git push`，未修改 `backend/.env`。

## 2. 本次完成内容

### 2.1 公共基础能力

已新增：

- `backend/settings/config.py`
  - 统一读取 `PETMALL_` 环境变量。
  - 默认读取 `backend/.env`。
- `backend/models/base.py`
  - SQLAlchemy `Base`。
  - `TimestampMixin`。
- `backend/models/database.py`
  - async engine。
  - `AsyncSessionLocal`。
- `backend/core/auth.py`
  - Argon2 密码哈希。
  - JWT 生成和解析。
  - `token_version` 支持。
- `backend/core/cache.py`
  - Redis cache 封装。
- `backend/core/dependencies.py`
  - `get_db`。
  - `get_current_user`。
  - `require_admin`。
  - `require_merchant`。
- `backend/core/errors.py`
  - 统一业务异常。
- `backend/core/response.py`
  - 统一响应结构预留。
- `backend/main.py`
  - 注册 CORS。
  - 注册 `/generated` 静态目录。
  - 注册 `auth_router`、`user_router`。

### 2.2 用户与鉴权

已新增：

- `backend/models/user.py`
- `backend/schemas/auth_schema.py`
- `backend/schemas/user_schema.py`
- `backend/repository/user_repository.py`
- `backend/services/auth_service.py`
- `backend/services/user_service.py`
- `backend/routers/auth_router.py`
- `backend/routers/user_router.py`

已实现能力：

- 手机号验证码发送。
- 用户注册。
- 用户登录。
- Token 刷新。
- 无状态退出。
- 当前用户信息读取。
- 当前用户资料更新。
- 修改密码后旧 Token 失效。
- 冻结用户、软删除用户禁止登录。

### 2.3 地址管理

已实现能力：

- 地址列表。
- 新增地址。
- 修改地址。
- 删除地址。
- 设置默认地址。
- 每个用户只允许一个默认地址。
- 删除默认地址后自动选择最近更新的未删除地址作为默认地址。
- 地址软删除。
- 预留订单模块读取地址快照方法：

```python
async def get_address_snapshot(db: AsyncSession, user_id: int, address_id: int) -> dict
```

### 2.4 短信验证码

参考 `E:\AISource\项目开发\secondProject\发送短信开发.pdf`，已按阿里云“号码认证服务（短信认证）”接入计划实现。

关键点：

- SDK：`alibabacloud_dypnsapi20170525`。
- endpoint：`dypnsapi.aliyuncs.com`。
- 测试模板：`100001`。
- 模板参数：`code`、`min`。
- 验证码由后端生成 6 位数字。
- Redis key：`sms:code:{phone}`。
- 验证码有效期：默认 300 秒。
- 发送冷却：默认 60 秒。
- 正式环境不返回明文验证码。
- 阿里云免资质测试通道需要先绑定测试手机号。

## 3. 已暴露接口

### 3.1 Auth

```http
POST /auth/code
POST /auth/register
POST /auth/login
POST /auth/logout
POST /auth/refresh
POST /auth/change-password
```

说明：

- `POST /auth/change-password` 已实现。
- 计划中的主路径 `POST /users/me/change-password` 也已实现。

### 3.2 Users

```http
GET    /users/me
PUT    /users/me/profile
POST   /users/me/change-password
GET    /users/me/addresses
POST   /users/me/addresses
PUT    /users/me/addresses/{address_id}
DELETE /users/me/addresses/{address_id}
POST   /users/me/addresses/{address_id}/default
```

## 4. 数据库与迁移

已新增 Alembic 配置：

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`

已新增迁移：

- `backend/alembic/versions/0001_user_auth_profile_address.py`

迁移包含三张表：

- `user`
- `user_profile`
- `user_address`

执行迁移命令：

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

查看迁移头：

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic heads
```

当前验证结果：

```text
0001_user_auth_profile_address (head)
```

## 5. 配置与依赖

### 5.1 已修改配置模板

已补充 `backend/.env.example`：

```env
PETMALL_RABBITMQ_URL=amqp://guest:guest@127.0.0.1:5672/
PETMALL_VECTOR_STORE_DIR=generated/vector_store
PETMALL_ALIYUN_SMS_ACCESS_KEY_ID=
PETMALL_ALIYUN_SMS_ACCESS_KEY_SECRET=
PETMALL_ALIYUN_SMS_SIGN_NAME=
PETMALL_ALIYUN_SMS_TEMPLATE_CODE=100001
PETMALL_ALIYUN_SMS_ENDPOINT=dypnsapi.aliyuncs.com
PETMALL_SMS_CODE_EXPIRE_SECONDS=300
PETMALL_SMS_SEND_COOLDOWN_SECONDS=60
PETMALL_SMS_DEBUG_CODE_ENABLED=false
PETMALL_PAYMENT_MODE=mock
```

注意：

- 没有修改 `backend/.env`。
- 真实 AK/SK 不得提交。
- `PETMALL_SMS_DEBUG_CODE_ENABLED=true` 只允许本地联调使用。

### 5.2 已新增依赖

已在 `backend/requirements.txt` 增加：

```text
alibabacloud_dypnsapi20170525
```

本次验证时，完整 `backend/requirements.txt` 安装因依赖较多超时，实际安装了第一阶段所需的最小依赖集完成测试。

后续 Agent/RAG 阶段需要继续安装完整依赖。

## 6. 验证结果

已执行：

```powershell
.\.venv\Scripts\python.exe -m compileall backend
```

结果：通过。

已执行：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

结果：

```text
4 passed
```

已执行：

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic heads
```

结果：

```text
0001_user_auth_profile_address (head)
```

## 7. 测试覆盖

测试文件：

- `backend/tests/conftest.py`
- `backend/tests/test_auth_user_address.py`

覆盖内容：

- 手机号格式错误不发送验证码。
- 短信验证码发送成功。
- 验证码写入 Redis。
- 同一手机号 60 秒内重复发送失败。
- 注册成功。
- 手机号重复注册失败。
- 登录成功。
- 用户资料读取。
- 用户资料更新。
- 修改密码后旧 Token 失效。
- 新密码可登录。
- 冻结用户禁止登录。
- 软删除用户禁止登录。
- 新增地址。
- 默认地址唯一。
- 越权修改他人地址失败。
- 删除默认地址后自动切换默认地址。

## 8. 当前工作树状态

本次新增或修改的主要文件：

- `backend/.env.example`
- `backend/requirements.txt`
- `backend/main.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/0001_user_auth_profile_address.py`
- `backend/core/auth.py`
- `backend/core/cache.py`
- `backend/core/dependencies.py`
- `backend/core/errors.py`
- `backend/core/response.py`
- `backend/models/base.py`
- `backend/models/database.py`
- `backend/models/user.py`
- `backend/repository/user_repository.py`
- `backend/routers/auth_router.py`
- `backend/routers/user_router.py`
- `backend/schemas/auth_schema.py`
- `backend/schemas/user_schema.py`
- `backend/services/auth_service.py`
- `backend/services/sms_service.py`
- `backend/services/user_service.py`
- `backend/settings/config.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth_user_address.py`

编译和测试会生成 `__pycache__`，当前 `.gitignore` 已忽略。

## 9. 后续接手建议

1. 本地启动前复制配置：

```powershell
Copy-Item backend\.env.example backend\.env
```

然后在 `backend/.env` 中填写本地 MySQL、Redis 和阿里云短信测试参数。

2. 启动依赖服务：

- MySQL 8。
- Redis。

3. 执行迁移：

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

4. 启动后端：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

5. Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

6. B 同学创建订单时，优先调用 `services.user_service.get_address_snapshot` 获取地址快照，不要直接跨层读取地址表。

7. C 同学做后台用户管理时，复用 `User.is_frozen`、`User.is_deleted`、`User.real_name_status`，不要另建用户状态字段。

## 10. 风险与注意事项

- 当前短信验证码正式发送依赖阿里云 AK/SK、签名名称和测试手机号绑定。
- `PETMALL_SMS_DEBUG_CODE_ENABLED=true` 只适合本地联调，不能用于演示真实验证码安全流程。
- 当前 `logout` 是无状态退出，由客户端删除 Token；如果后续需要服务端强制退出，可增加 Token blacklist 或 user session 表。
- 当前测试使用 SQLite 内存库，真实环境使用 MySQL；上线前需要在 MySQL 上执行迁移验证。
- `docs/` 当前被 `.gitignore` 忽略，本文档不会自动进入 Git 提交。
