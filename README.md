# SMIP - Smart Money Intelligence Platform

智能资金情报平台：生产级加密货币分析系统，支持智能资金追踪、清算地图、订单簿热力图与交易信号。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| **仪表盘** | 市场概览、最新信号、近期清算、顶级智能资金 |
| **顶级交易者** | 按综合评分排名，展示真实胜率、最大回撤、盈亏比、交易次数 |
| **智能信号** | 多智能资金同向建仓时触发的交易信号与置信度 |
| **清算地图** | ECharts 交互式热力图，1h/4h/24h 时间窗口，当前价标线 |
| **订单簿热力图** | 深度图、买卖力量比、鲸鱼挂单标注、5 秒刷新 |
| **市场概览** | 价格、持仓量（真实多空比）、资金费率、成交量 |

## 技术栈

- **后端**: FastAPI, SQLAlchemy (async), PostgreSQL 15+, Redis 7+, Uvicorn
- **前端**: Next.js 14, React 18, Tailwind CSS, ECharts 5
- **数据采集**: Binance / OKX WebSocket + REST，Hyperliquid API
- **部署**: Docker Compose, Nginx, systemd（采集器）

## 架构说明

- **新加坡服务器（核心）**: PostgreSQL、Redis、Backend API、Frontend、Nginx，对外仅开放 80 端口
- **东京服务器（采集器）**: 独立进程连接新加坡 DB/Redis，采集 Binance/OKX/Hyperliquid 数据

## 快速开始（本地开发）

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/smip.git && cd smip

# 2. 环境变量
cp .env.example .env   # 编辑 .env 填入数据库与 Redis 配置

# 3. 启动核心服务（需已安装 Docker）
docker compose up -d

# 4. 访问
# 前端: http://localhost
# API 文档: http://localhost/docs
```

## 外部 API

所有接口以 JSON 返回，基础路径：`/api`。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/top-traders` | GET | 顶级交易者列表，支持 `limit`、`offset` |
| `/api/trader/{wallet}` | GET | 指定钱包的详情与近期交易 |
| `/api/signals` | GET | 交易信号，可选 `symbol`、`limit` |
| `/api/liquidations` | GET | 近期清算事件，可选 `symbol`、`limit` |
| `/api/liquidation-map` | GET | 清算地图数据，`symbol`、`timeframe`(1h/4h/24h) |
| `/api/orderbook` | GET | 订单簿快照，含买卖比与鲸鱼单，`symbol` |
| `/api/open-interest` | GET | 持仓量（多空比），可选 `symbol`、`limit` |
| `/api/funding-rates` | GET | 资金费率，可选 `symbol`、`limit` |
| `/api/market-overview` | GET | 市场概览（价格与成交量） |
| `/api/health` | GET | 健康检查 |

完整 Schema 与在线调试请访问部署后的 **Swagger UI**：`http://your-domain/docs`，或 **ReDoc**：`http://your-domain/redoc`。

## 中英文切换

前端支持中文 / English 切换，侧边栏底部可切换语言。

## 文档与部署

- [部署指南 (DEPLOYMENT.md)](./DEPLOYMENT.md)：新加坡 + 东京双机部署、防火墙、采集器 systemd 配置
- [项目详细设计 (SMIP-Documentation)](../SMIP-Documentation/)：架构、数据库、API 与业务说明（若已存在）

## 许可证

Private repository. All rights reserved.
