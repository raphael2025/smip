# SMIP 部署指南

本文档说明如何在 **新加坡服务器（核心）** 与 **东京服务器（采集器）** 上完整部署 SMIP。

---

## 一、前置要求

- 新加坡服务器：建议 4H8G+，安装 Docker 与 Docker Compose
- 东京服务器：建议 2H2G+，用于运行数据采集器（Python 3.10+）
- 新加坡服务器已开放 80 端口；东京服务器需能访问新加坡的 5432（PostgreSQL）、6379（Redis）

---

## 二、新加坡服务器部署（核心系统）

### 2.1 安装 Docker（若未安装）

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 登出再登录后生效
```

### 2.2 上传项目

将本仓库克隆或打包上传到新加坡服务器，例如：

```bash
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/smip.git
cd smip
```

### 2.3 配置环境变量

```bash
cp .env.example .env
chmod 600 .env
```

编辑 `.env`，至少设置：

```env
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=smip
DATABASE_USER=smip_user
DATABASE_PASSWORD=你的强密码

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=你的Redis密码

BINANCE_API_KEY=可选，若需私有接口
BINANCE_API_SECRET=可选

API_HOST=0.0.0.0
API_PORT=8000
```

说明：在 Docker Compose 中，`DATABASE_HOST`/`REDIS_HOST` 使用服务名 `postgres`/`redis`，无需改为公网 IP。

### 2.4 构建并启动

```bash
cd /home/ubuntu/smip
docker compose build --no-cache
docker compose up -d
```

检查服务状态：

```bash
docker compose ps
curl -s http://localhost/api/health
```

应返回 `{"status":"healthy",...}`。

### 2.5 防火墙（推荐）

仅开放必要端口，并仅允许东京 IP 访问数据库与 Redis：

```bash
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
# 将 东京服务器公网IP 替换为实际 IP
sudo ufw allow from 东京服务器公网IP to any port 5432
sudo ufw allow from 东京服务器公网IP to any port 6379
sudo ufw --force enable
sudo ufw status verbose
```

---

## 三、东京服务器部署（数据采集器）

### 3.1 安装依赖

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
cd /home/ubuntu/smip/collector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

若没有 `requirements.txt`，可安装：

```bash
pip install aiohttp websockets sqlalchemy[asyncio] asyncpg pydantic-settings python-dotenv
```

### 3.2 采集器环境变量

```bash
cp .env.example .env
chmod 600 .env
```

编辑 `collector/.env`，**指向新加坡服务器**：

```env
DATABASE_HOST=新加坡服务器公网IP
DATABASE_PORT=5432
DATABASE_NAME=smip
DATABASE_USER=smip_user
DATABASE_PASSWORD=与新加坡 .env 中一致

REDIS_HOST=新加坡服务器公网IP
REDIS_PORT=6379
REDIS_PASSWORD=与新加坡 .env 中一致

BINANCE_API_KEY=可选
BINANCE_API_SECRET=可选
```

### 3.3 安装并启动 systemd 服务

```bash
sudo cp /home/ubuntu/smip/collector/smip-collector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smip-collector
sudo systemctl start smip-collector
sudo systemctl status smip-collector
```

日志查看：

```bash
sudo journalctl -u smip-collector -f
```

### 3.4 首次部署后：全量重算交易者指标（可选）

若数据库已有历史数据且希望按最新逻辑重算所有交易者的 max_drawdown、profit_factor、score：

```bash
cd /home/ubuntu/smip
source collector/venv/bin/activate
# 使用采集器 .env 连接新加坡 DB
python3 scripts/recalculate_metrics.py
```

---

## 四、验证清单

| 项 | 命令/方式 |
|----|-----------|
| 新加坡 API 健康 | `curl http://新加坡IP/api/health` |
| 新加坡前端 | 浏览器打开 `http://新加坡IP` |
| API 文档 | `http://新加坡IP/docs` |
| 采集器运行 | `sudo systemctl status smip-collector` |
| 采集器连库 | 日志中可见 "Database: 新加坡IP:5432" 及 "Tracking N wallets" |

---

## 五、日常运维

- **重启核心**：`cd /home/ubuntu/smip && docker compose restart`
- **重启采集器**：`sudo systemctl restart smip-collector`
- **查看采集器日志**：`sudo journalctl -u smip-collector -n 100 --no-pager`
- **数据库备份**：`docker exec smip-postgres pg_dump -U smip_user smip > backup_$(date +%Y%m%d).sql`

---

## 六、故障排查

- **502 Bad Gateway**：检查 `docker compose ps` 中 backend/frontend 是否均为 Up，并查看 `docker compose logs backend`。
- **采集器无法连库**：确认新加坡防火墙已放行东京 IP 的 5432/6379；确认 `collector/.env` 中 `DATABASE_HOST`/`REDIS_HOST` 为新加坡公网 IP。
- **交易次数/指标异常**：运行一次 `scripts/recalculate_metrics.py` 做全量重算。
