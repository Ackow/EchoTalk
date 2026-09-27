# EchoTalk 2.0

EchoTalk 2.0 当前提供账户注册、登录、退出，以及登录后的空白工作区。场景练习、语音、历史、分析、设置和 RAG 尚未实现。

## 技术结构

- `frontend/`：Vue 3、Vite 与 Electron 桌面客户端。
- `backend/`：FastAPI 账户 API；运行时连接 MySQL，不再使用 SQLite。
- `frontend-1.0/`、`backend-1.0/`：旧版参考代码，不由 2.0 启动。
- `EchoTalk-2.0-Design-Package/`：产品与界面设计参考。

## 本地开发

需要 Node.js 18+、Python 3.12.10、uv 和 MySQL 8。本机 MySQL 开发默认端口为 `3307`。

### 配置并启动后端

复制 `backend/.env.example` 为 `backend/.env`，填写自己的数据库信息。该文件已加入忽略规则，不要把实际密码提交到版本库。

首次使用本机 MySQL 时，先用有建库权限的账户创建数据库，并为 `.env` 中的应用用户授予该库的读写与建表权限：

```sql
CREATE DATABASE echotalk CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

云数据库则在服务商控制台创建同名数据库并授权应用用户；后端的 `init_db.py` 只创建账户表，不负责创建 MySQL 数据库本身。

```dotenv
ECHOTALK_DB_HOST=127.0.0.1
ECHOTALK_DB_PORT=3307
ECHOTALK_DB_NAME=echotalk
ECHOTALK_DB_USER=你的数据库用户名
ECHOTALK_DB_PASSWORD=你的数据库密码
ECHOTALK_DB_SSL_CA=
ECHOTALK_API_HOST=127.0.0.1
ECHOTALK_API_PORT=8000
ECHOTALK_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,null
```

`ECHOTALK_DB_SSL_CA` 用于填写云数据库提供的 CA 证书文件路径；本地回环地址 MySQL 可留空，远程数据库缺少 CA 配置时后端会拒绝启动。远程连接会验证证书链和主机名。部署到云端时，将 host、port、库名、用户名、密码替换为云实例配置，并将 CORS 来源改为实际 Web 客户端域名；Electron 安装包使用 `file://` 来源时保留 `null`。云部署也可通过环境变量注入相同字段，无需修改代码。

```bash
cd backend
uv sync --locked --cache-dir .uv-cache
uv run --cache-dir .uv-cache python init_db.py
uv run --cache-dir .uv-cache python main.py
```

`init_db.py` 是显式建表步骤；API 导入或启动不会自动连接数据库执行 DDL。2.0 后端环境固定在 `backend/.venv`，仓库根目录 `.venv` 是旧环境，运行 2.0 时不要激活它。PyMySQL 使用 SQLAlchemy `URL.create()` 组装连接配置，密码中的特殊字符无需拼接或手工转义。

API 默认监听 `127.0.0.1:8000`。云端部署时可设 `ECHOTALK_API_HOST=0.0.0.0`，并使用 HTTPS 反向代理转发到该服务；不要直接将未加密的 Uvicorn 端口暴露到公网。

### 配置并启动前端

复制 `frontend/.env.example` 为 `frontend/.env.local`。开发默认地址是本机后端：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Web 浏览器开发：

```bash
cd frontend
npm ci
npm run dev
```

Electron 桌面开发（命令会自行启动 Vite）：

```bash
cd frontend
npm ci
npm run electron:dev
```

桌面正式包连接云服务时，创建未提交的 `frontend/.env.production.local`，将 `VITE_API_BASE_URL` 设为云端 HTTPS API 地址（例如 `https://api.example.com`），再运行打包命令。Vite 会将这个地址用于身份 API 与内容安全策略白名单；网页和 Electron 共用同一配置，不再从 Electron 主进程固定读取本机地址。

```bash
cd frontend
npm run pack
```

后端 CORS 只允许 `ECHOTALK_CORS_ORIGINS` 中列出的来源；不要在生产环境设置为通配符。Electron 窗口使用应用内标题栏，标题栏空白区域可拖动，右上角提供最小化、最大化/还原和关闭操作。

首次注册至少使用 3 位用户名和 8 位密码。密码以 PBKDF2-SHA256 哈希保存，退出会撤销当前登录会话。
