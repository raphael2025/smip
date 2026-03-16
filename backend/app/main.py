import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router as api_router
from app.database import get_redis

logger = logging.getLogger("smip")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis unavailable at startup, will use fallback: {e}")
    yield
    try:
        redis = await get_redis()
        await redis.close()
    except Exception:
        pass


app = FastAPI(
    title="SMIP - Smart Money Intelligence Platform",
    description=(
        "Production-grade crypto analytics API providing smart money tracking, "
        "liquidation maps, orderbook heatmaps, and trading signals.\n\n"
        "生产级加密货币分析API，提供智能资金追踪、清算地图、订单簿热力图和交易信号。"
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# D5: Tightened CORS - allow specific origin + wildcard without credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://43.128.77.234", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "Smart Money Intelligence Platform (SMIP)",
        "version": "1.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "api": "/api",
    }
