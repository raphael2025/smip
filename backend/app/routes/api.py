from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.market_service import (
    get_top_traders, get_trader_detail, get_signals,
    get_liquidations, get_liquidation_map, get_orderbook,
    get_open_interest_data, get_funding_rates, get_market_overview,
)

router = APIRouter(prefix="/api", tags=["Market Data"])


@router.get("/top-traders",
    summary="Get Top Traders",
    description="Returns ranked list of top traders by composite score including real max_drawdown and profit_factor.")
async def api_top_traders(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    data = await get_top_traders(db, limit, offset)
    return {"status": "success", "data": data, "count": len(data)}


@router.get("/trader/{wallet}",
    summary="Get Trader Detail",
    description="Returns detailed metrics and recent trades for a specific trader.")
async def api_trader_detail(
    wallet: str,
    db: AsyncSession = Depends(get_db),
):
    data = await get_trader_detail(db, wallet)
    if not data:
        raise HTTPException(status_code=404, detail="Trader not found")
    return {"status": "success", "data": data}


@router.get("/signals",
    summary="Get Trading Signals",
    description="Returns latest smart money trading signals with confidence scores.")
async def api_signals(
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    data = await get_signals(db, symbol, limit)
    return {"status": "success", "data": data, "count": len(data)}


@router.get("/liquidations",
    summary="Get Recent Liquidations",
    description="Returns recent forced liquidation events from CEX.")
async def api_liquidations(
    symbol: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    data = await get_liquidations(db, symbol, limit)
    return {"status": "success", "data": data, "count": len(data)}


@router.get("/liquidation-map",
    summary="Get Liquidation Map",
    description="Returns liquidation cluster distribution for heatmap with timeframe support (1h/4h/24h).")
async def api_liquidation_map(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("24h", regex="^(1h|4h|24h)$"),
    db: AsyncSession = Depends(get_db),
):
    data = await get_liquidation_map(db, symbol, timeframe)
    return {"status": "success", "data": data}


@router.get("/orderbook",
    summary="Get Orderbook Depth",
    description="Returns latest orderbook snapshot with bid/ask ratio and whale order detection.")
async def api_orderbook(
    symbol: str = Query("BTCUSDT"),
    db: AsyncSession = Depends(get_db),
):
    data = await get_orderbook(db, symbol)
    return {"status": "success", "data": data}


@router.get("/open-interest",
    summary="Get Open Interest",
    description="Returns open interest data with real long/short breakdown from Binance.")
async def api_open_interest(
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    data = await get_open_interest_data(db, symbol, limit)
    return {"status": "success", "data": data, "count": len(data)}


@router.get("/funding-rates",
    summary="Get Funding Rates",
    description="Returns historical funding rates for perpetual contracts.")
async def api_funding_rates(
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    data = await get_funding_rates(db, symbol, limit)
    return {"status": "success", "data": data, "count": len(data)}


@router.get("/market-overview",
    summary="Get Market Overview",
    description="Returns latest price and volume data for all tracked symbols.")
async def api_market_overview(
    db: AsyncSession = Depends(get_db),
):
    data = await get_market_overview(db)
    return {"status": "success", "data": data, "count": len(data)}


@router.get("/health",
    summary="Health Check")
async def health_check():
    return {"status": "healthy", "service": "SMIP API", "version": "1.1.0"}
