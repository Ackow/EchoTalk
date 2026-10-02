# EchoTalk 2.0 后端 + MySQL 云端部署手册（Ubuntu 26.04）

目标：把后端 API 和 MySQL 数据库部署到一台 Ubuntu 云服务器，多端（网页 / Electron 桌面端）统一访问同一个云端数据库，实现数据同步。

## 架构总览

```
多端客户端（网页 / Electron）
        │  HTTPS (443)
        ▼
   Nginx 反向代理  ──  Let's Encrypt 证书
        │  HTTP (127.0.0.1:8000)
        ▼
   uvicorn (FastAPI, systemd 托管, 2 workers)
        │  TCP (127.0.0.1:3306)
        ▼
   MySQL 8（仅监听本机回环，不对公网开放）
```

核心原则：

- **数据库绝不对公网开放**。API 与 MySQL 同机，MySQL 只监听 `127.0.0.1`，外部只能通过 API 访问数据。
- **API 只监听 `127.0.0.1`**，对外统一走 Nginx 的 80/443，由 Nginx 负责 HTTPS。
- 依赖用 **uv** 按 `uv.lock` 精确安装，Python 3.12 由 uv 自行管理（Ubuntu 26.04 自带的 Python 是 3.13，不满足项目 `>=3.12,<3.13` 的要求）。

---

## 第 0 步：准备服务器

假设你有一台全新的 Ubuntu 26.04 云主机，能以 root 或 sudo 用户 SSH 登录。需要一个域名（如 `api.your-domain.com`）并把它 A 记录解析到服务器公网 IP；没有域名也可以先用 IP 跑 HTTP，但 Electron/网页跨端场景强烈建议上 HTTPS。

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 创建部署专用用户（避免用 root 跑服务）
sudo adduser deploy
sudo usermod -aG sudo deploy

# 配置防火墙：只放行 SSH / HTTP / HTTPS，注意不放行 3306 和 8000
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

建议同时给 `deploy` 用户配置 SSH 密钥登录并关闭密码登录（`/etc/ssh/sshd_config` 中 `PasswordAuthentication no`），然后安装 fail2ban 防爆破：`sudo apt install fail2ban -y`。

---

## 第 1 步：安装 MySQL 8 并初始化数据库

```bash
sudo apt install mysql-server -y
sudo systemctl enable --now mysql

# 确认 MySQL 只监听本机（Ubuntu 默认即是）
sudo ss -tlnp | grep 3306    # 应显示 127.0.0.1:3306，而不是 0.0.0.0:3306
```

创建库和账号（把 `YourStrongPassword` 换成强密码）：

```bash
sudo mysql <<'SQL'
CREATE DATABASE echotalk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'echotalk_app'@'localhost' IDENTIFIED BY 'YourStrongPassword';
GRANT ALL PRIVILEGES ON echotalk.* TO 'echotalk_app'@'localhost';
FLUSH PRIVILEGES;
SQL
```

> 说明：账号限定 `@'localhost'`，即使将来误开 3306 外部也无法登录。项目 `app/core/config.py` 默认库名 `echotalk`、用户 `echotalk_app`，与此对应；本地开发用的 3307 端口在云端用 Ubuntu 默认的 3306 即可，通过 `.env` 覆盖。

### 附：测试环境开放 MySQL 外部访问（阿里云等云主机）

生产环境不要这么做；仅当本地开发机需要直连云端库时临时使用。云主机上外部访问需要**四处同时放行**，缺一不可：

```bash
# ① MySQL 监听所有网卡（默认只听 127.0.0.1）
sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo systemctl restart mysql && sudo ss -tlnp | grep 3306   # 应显示 0.0.0.0:3306

# ② 账号允许任意主机登录（@'%' 而非 @'localhost'）
sudo mysql <<'SQL'
CREATE USER 'echotalk_app'@'%' IDENTIFIED WITH caching_sha2_password BY 'YourStrongPassword';
GRANT ALL PRIVILEGES ON echotalk.* TO 'echotalk_app'@'%';
FLUSH PRIVILEGES;
SQL

# ③ 系统防火墙
sudo ufw allow 3306/tcp
```

# ④ 云厂商安全组（阿里云控制台 → ECS → 安全组 → 入方向规则）：放行 TCP 3306

本地验证：`mysql -h <公网IP> -P 3306 -u echotalk_app -p`。测试结束建议把安全组规则改为仅允许自己的 IP，或删除规则恢复仅本机访问。

### 附：root 直跑的调整

若不创建 deploy 用户、直接以 root 操作：初始化/更新脚本无需改动，直接 `bash deploy/server-init.sh` 执行即可；但 systemd 服务建议保持独立用户，或把 `echotalk-backend.service` 中的 `User=`/`Group=` 改为 `root`，并删除单元文件中的 `ProtectHome=read-only` 等与 root 冲突的加固项。

---

## 第 2 步：安装 uv 并让服务器能从 GitHub 拉代码

### 2.1 配置部署密钥（Deploy Key，一次性）

服务器不需要你的 GitHub 账号密码，只需一把**只读部署密钥**，专门用于从仓库拉代码：

```bash
# 服务器上生成专用密钥对（以 deploy 用户执行，一路回车即可）
ssh-keygen -t ed25519 -C "echotalk-server-deploy" -f ~/.ssh/echotalk_deploy -N ""

# 告诉 ssh 访问 github.com 时使用这把密钥
cat >> ~/.ssh/config <<'CONF'
Host github.com
  IdentityFile ~/.ssh/echotalk_deploy
  IdentitiesOnly yes
CONF
chmod 600 ~/.ssh/config

# 打印公钥内容，复制整行（ssh-ed25519 开头）
cat ~/.ssh/echotalk_deploy.pub
```

然后到 GitHub 仓库页面添加公钥：  
**Ackow/EchoTalk → Settings → Deploy keys → Add deploy key**，粘贴公钥内容，**不要**勾选 "Allow write access"（服务器只需要读权限，密钥泄露也无法改代码）。

验证连通性：

```bash
ssh -T git@github.com
# 预期输出：Hi Ackow/EchoTalk! You've successfully authenticated, but GitHub does not provide shell access.
```

> **找不到 Deploy keys？**  
> 直达链接：`https://github.com/Ackow/EchoTalk/settings/keys`。  
> 注意它位于**仓库**的 Settings（进入仓库页面后顶部的 Settings 标签）→ 左侧栏 Security 分组，不是个人账号设置；看不到 Settings 标签说明当前账号没有该仓库的管理员权限。  
> 如果仍不可用，可改用 HTTPS + 个人访问令牌（PAT）方式：
>
> 1. GitHub 个人 Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token
> 2. Repository access 选 "Only select repositories" 并勾选 EchoTalk；Permissions 中 Contents 设为 **Read-only**
> 3. 服务器上改用 HTTPS 远端并写入令牌：
>    ```bash
>    git clone https://<你的TOKEN>@github.com/Ackow/EchoTalk.git /opt/echotalk
>    ```
>    注意令牌会明文存在 `/opt/echotalk/.git/config` 中，执行 `chmod 600 /opt/echotalk/.git/config` 收紧权限，且令牌只给 Contents:Read-only 权限以降低泄露风险。

### 2.2 安装 uv 并首次克隆

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # 或重新登录使 PATH 生效
uv --version

# 首次克隆（之后 git pull 无需再配置任何东西）
sudo mkdir -p /opt/echotalk
sudo chown deploy:deploy /opt/echotalk
git clone git@github.com:Ackow/EchoTalk.git /opt/echotalk
cd /opt/echotalk/backend
```

之后的日常发布流程就是三步：

```bash
# ① 本地开发机：提交并推送
git add -A && git commit -m "..." && git push

# ② 服务器：一键更新（内部就是 git pull --ff-only）
bash /opt/echotalk/backend/deploy/update.sh
```

> **脚本速查**
>
> | 脚本                      | 用途                                                        | 执行时机              |
> | ----------------------- | --------------------------------------------------------- | ----------------- |
> | `deploy/server-init.sh` | 装依赖 + **只拉取 backend/**（sparse checkout）+ 生成 .env + 初始化数据库 | 服务器首次部署，可重复执行（幂等） |
> | `deploy/update.sh`      | 备份 → 拉最新代码 → 同步依赖 → 初始化表 → 重启 → 健康检查                      | 后端每次迭代后           |
>
> Deploy key 配好并完成首次克隆后，第 2.2 节和第 3、4 步可以整体用一条命令代替：
>
> ```bash
> bash /opt/echotalk/backend/deploy/server-init.sh
> ```
>
> 若仓库已全量克隆过，脚本会自动把它收窄为只检出 `backend/`，前端/docs 不会占用服务器磁盘。

安装依赖（uv 会读取 `.python-version` = 3.12.10，若服务器上没有会自动下载对应的 CPython 3.12）：

```bash
cd /opt/echotalk/backend
uv sync
# 验证
uv run python -c "import fastapi, sqlalchemy, pymysql, uvicorn; print('deps OK')"
```

---

## 第 3 步：配置生产环境 `.env`

```bash
cd /opt/echotalk/backend
cp deploy/.env.production.example .env
nano .env
```

必须修改的项：

| 配置项                     | 值                 | 说明                                                                                                       |
| ----------------------- | ----------------- | -------------------------------------------------------------------------------------------------------- |
| `ECHOTALK_DB_PASSWORD`  | MySQL 第 1 步设置的强密码 | 不填后端启动即报错                                                                                                |
| `ECHOTALK_DB_PORT`      | `3306`            | 云端用 Ubuntu 默认端口，非本地的 3307                                                                                |
| `ECHOTALK_CORS_ORIGINS` | 你的前端实际来源          | 网页端填 `https://你的域名`；Electron 打包版（file:// 协议）Origin 为 `null`，必须保留 `null`；本地调试可临时加 `http://localhost:5173` |

---

## 第 4 步：初始化数据表和场景包种子

项目不会自动执行 DDL，需手动跑一次：

```bash
cd /opt/echotalk/backend
uv run python init_db.py
# 预期输出：EchoTalk 数据表已初始化，内置场景包同步 N 个。
```

**迁移旧数据（可选）**：如果本地 MySQL 里已有数据，先在本地导出再导入云端：

root@iZbp18ynntkrbwzej1vb81Z:~~# sudo adduser deploy  
New password:  
Retype new password:  
Sorry, passwords do not match.  
passwd: Authentication token manipulation error  
passwd: password unchanged  
warn: \`/bin/passwd deploy' failed with status 10. Continuing.  
warn: wrong password given or password retyped incorrectly  
Try again? [y/N] y  
New password:  
Retype new password:  
passwd: password updated successfully  
Changing the user information for deploy  
Enter the new value, or press ENTER for the default  
Full Name []:  
Room Number []:  
Work Phone []:  
Home Phone []:  
Other []:  
Is the information correct? [Y/n]  
root@iZbp18ynntkrbwzej1vb81Z:~~# sudo usermod -aG sudo deploy  
root@iZbp18ynntkrbwzej1vb81Z:~~# sudo ufw allow OpenSSH  
sudo ufw allow 80/tcp  
sudo ufw allow 443/tcp  
sudo ufw enable  
sudo ufw statusRules updated  
Rules updated (v6)  
root@iZbp18ynntkrbwzej1vb81Z:~~# sudo apt install mysql-server -y  
Error: Unable to locate package mysql-server  
root@iZbp18ynntkrbwzej1vb81Z:~#

---

## 第 5 步：配置 systemd 常驻服务

```bash
sudo cp /opt/echotalk/backend/deploy/echotalk-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now echotalk-backend
sudo systemctl status echotalk-backend      # 应为 active (running)
curl http://127.0.0.1:8000/docs -o /dev/null -w "%{http_code}\n"   # 预期 200
```

常用运维命令：

```bash
sudo systemctl restart echotalk-backend   # 重启
journalctl -u echotalk-backend -f         # 看实时日志
journalctl -u echotalk-backend --since today
```

---

## 第 6 步：Nginx 反向代理 + HTTPS

```bash
sudo apt install nginx certbot python3-certbot-nginx -y

# 安装站点配置（记得先把 server_name 改成你的域名）
sudo cp /opt/echotalk/backend/deploy/nginx-echotalk.conf /etc/nginx/sites-available/echotalk
sudo nano /etc/nginx/sites-available/echotalk     # 修改 server_name
sudo ln -s /etc/nginx/sites-available/echotalk /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 一条命令签发 HTTPS 证书并自动改写 Nginx 配置（含自动续期）
sudo certbot --nginx -d api.your-domain.com
```

验证：浏览器访问 `https://api.your-domain.com/docs` 能打开 Swagger 页面即部署成功。

---

## 第 7 步：客户端接入

所有端把 API 地址从本地地址改为云端地址即可，数据天然同步（同一后端、同一数据库）：

- **网页端**：前端构建时的 API base URL 指向 `https://api.your-domain.com`，并确认该来源已在 `ECHOTALK_CORS_ORIGINS` 中。
- **Electron 桌面端**：API base URL 同样指向云端地址；file:// 加载时 Origin 为 `null`，`ECHOTALK_CORS_ORIGINS` 里必须包含 `null`（模板已包含）。

---

## 文件存储：后端落盘文件如何集中管理

后端除了数据库，还负责把文件写到磁盘（这也是必须**只部署一个云端后端**的原因——各端只是客户端，所有上传、存储都发生在服务器上，天然一致，不存在跨设备文件不匹配的问题）：

| 文件类型               | 落盘位置                                           | 说明                              |
| ------------------ | ---------------------------------------------- | ------------------------------- |
| 场景知识资料（md/txt/pdf） | `backend/storage/scenes/{scene_id}/knowledge/` | 上传时写入，元数据入 `documents/chunks` 表 |
| 场景封面图              | `backend/storage/scenes/{scene_id}/cover.*`    | 上传时写入，路径存 `scenes.cover_path`   |

两个要点：

**① 存储目录与代码目录分离（推荐）**。存储根目录可用环境变量 `ECHOTALK_STORAGE_ROOT` 覆盖（`app/scenes/knowledge.py` 读取，默认 `backend/storage/`）。在 `.env` 中加：

```
ECHOTALK_STORAGE_ROOT=/data/echotalk/storage
```

这样用户文件放在独立数据盘上，`git pull` 更新代码时完全不影响文件；目录权限记得给 `deploy` 用户：

```bash
sudo mkdir -p /data/echotalk/storage
sudo chown deploy:deploy /data/echotalk/storage
```

**② 已有本地文件迁移到云端**。把开发机上的 `backend/storage/` 整体同步过去（若改了 `ECHOTALK_STORAGE_ROOT`，同步到对应目录）：

```bash
rsync -avz F:/Project/EchoTalk/backend/storage/ deploy@<服务器IP>:/data/echotalk/storage/
```

`backend/storage/` 已在 `.gitignore` 中（运行时用户数据不入库），不会干扰代码更新。

---

## 日常更新：一键更新脚本

后端迭代频繁，服务器更新已脚本化，一条命令完成 **备份 → 拉代码 → 同步依赖 → 初始化表 → 重启 → 健康检查**：

```bash
bash /opt/echotalk/backend/deploy/update.sh
```

脚本行为：

1. 更新前自动备份数据库（mysqldump + gzip）和 `storage/` 文件（tar + gzip）到 `/opt/echotalk/backups/`，自动清理 14 天前的旧备份
2. `git pull --ff-only` 拉取最新代码（有未推送的分叉会安全终止，不会静默合并）
3. `uv sync` 按 `uv.lock` 同步依赖
4. `uv run python init_db.py`（幂等：新建缺失的表、同步内置场景包种子，已有数据不受影响）
5. 重启 systemd 服务，并轮询 `/api/ready` 做健康检查
6. 失败时给出日志查看命令和回滚提示

本地开发机推代码后，SSH 到服务器跑这一条命令即可完成发布。

---

## 安全要点清单

- [ ] 防火墙只开放 22 / 80 / 443，**3306、8000 均未放行**
- [ ] MySQL 仅监听 `127.0.0.1`，账号限定 `@'localhost'`
- [ ] `.env` 权限收紧：`chmod 600 .env`（含数据库密码，且已确认被 `.gitignore` 排除、绝不入库）
- [ ] SSH 使用密钥登录、禁用密码，安装 fail2ban
- [ ] 全站 HTTPS（certbot 自动续期，`sudo certbot renew --dry-run` 可验证）
- [ ] 定期备份：数据库与 `storage/` 文件均由 `update.sh` 每次更新前自动备份；另建议 cron 每日备份并同步到对象存储

---

## 备选方案：Docker Compose（一键起 MySQL + API）

如果更想要可移植的容器化部署，可跳过第 1、5 步，写一个 `docker-compose.yml`（mysql:8 + 后端镜像，`network_mode` 内部互通），但当前项目尚无 Dockerfile，需先补齐。对单机部署而言，上文的"系统级 MySQL + systemd + Nginx"方案更简单直接，推荐优先使用。
