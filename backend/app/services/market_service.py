import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Trader, Trade, Signal, Liquidation,
    OrderbookSnapshot, OpenInterest, FundingRate, MarketTicker
)
from app.database import get_redis

logger = logging.getLogger("market_service")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


def to_json(data) -> str:
    return json.dumps(data, cls=DecimalEncoder)


def from_json(data: str):
    return json.loads(data)


async def get_cached_or_query(cache_key: str, ttl: int, query_func):
    """E4: Redis cache with fallback to direct DB query on failure."""
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return from_json(cached)
    except Exception as e:
        logger.warning(f"Redis read failed, falling back to DB: {e}")
        return await query_func()

    result = await query_func()
    try:
        redis = await get_redis()
        await redis.setex(cache_key, ttl, to_json(result))
    except Exception as e:
        logger.warning(f"Redis write failed: {e}")
    return result


async def get_top_traders(db: AsyncSession, limit: int = 50, offset: int = 0):
    async def query():
        stmt = (
            select(Trader)
            .order_by(desc(Trader.score))
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        traders = result.scalars().all()
        return [{
            "wallet_address": t.wallet_address,
            "total_pnl": float(t.total_pnl or 0),
            "win_rate": float(t.win_rate or 0),
            "trade_count": t.trade_count or 0,
            "max_drawdown": float(t.max_drawdown or 0),
            "profit_factor": float(t.profit_factor or 0),
            "score": float(t.score or 0),
            "is_smart_money": t.is_smart_money,
            "last_trade_time": t.last_trade_time.isoformat() if t.last_trade_time else None,
        } for t in traders]

    return await get_cached_or_query(f"top_traders:{limit}:{offset}", 300, query)


async def get_trader_detail(db: AsyncSession, wallet: str):
    async def query():
        stmt = select(Trader).where(Trader.wallet_address == wallet)
        result = await db.execute(stmt)
        t = result.scalar_one_or_none()
        if not t:
            return None

        trades_stmt = (
            select(Trade)
            .where(Trade.wallet_address == wallet)
            .order_by(desc(Trade.open_time))
            .limit(100)
        )
        trades_result = await db.execute(trades_stmt)
        trades = trades_result.scalars().all()

        return {
            "wallet_address": t.wallet_address,
            "total_pnl": float(t.total_pnl or 0),
            "win_rate": float(t.win_rate or 0),
            "trade_count": t.trade_count or 0,
            "max_drawdown": float(t.max_drawdown or 0),
            "avg_hold_time": str(t.avg_hold_time) if t.avg_hold_time else None,
            "profit_factor": float(t.profit_factor or 0),
            "score": float(t.score or 0),
            "is_smart_money": t.is_smart_money,
            "last_trade_time": t.last_trade_time.isoformat() if t.last_trade_time else None,
            "recent_trades": [{
                "id": tr.id,
                "symbol": tr.symbol,
                "side": tr.side,
                "size": float(tr.size),
                "entry_price": float(tr.entry_price),
                "exit_price": float(tr.exit_price) if tr.exit_price else None,
                "pnl": float(tr.pnl) if tr.pnl else None,
                "open_time": tr.open_time.isoformat(),
                "close_time": tr.close_time.isoformat() if tr.close_time else None,
                "leverage": float(tr.leverage) if tr.leverage else None,
                "source": tr.source,
            } for tr in trades],
        }

    return await get_cached_or_query(f"trader:{wallet}", 60, query)


async def get_signals(db: AsyncSession, symbol: Optional[str] = None, limit: int = 50):
    async def query():
        stmt = select(Signal).order_by(desc(Signal.created_at)).limit(limit)
        if symbol:
            stmt = stmt.where(Signal.symbol == symbol)
        result = await db.execute(stmt)
        signals = result.scalars().all()
        return [{
            "id": s.id,
            "symbol": s.symbol,
            "signal_type": s.signal_type,
            "confidence": float(s.confidence),
            "participants": s.participants,
            "avg_entry_price": float(s.avg_entry_price) if s.avg_entry_price else None,
            "total_size": float(s.total_size) if s.total_size else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        } for s in signals]

    cache_key = f"signals:{symbol or 'all'}:{limit}"
    return await get_cached_or_query(cache_key, 10, query)


async def get_liquidations(db: AsyncSession, symbol: Optional[str] = None, limit: int = 200):
    async def query():
        stmt = select(Liquidation).order_by(desc(Liquidation.timestamp)).limit(limit)
        if symbol:
            stmt = stmt.where(Liquidation.symbol == symbol)
        result = await db.execute(stmt)
        liqs = result.scalars().all()
        return [{
            "id": l.id,
            "symbol": l.symbol,
            "side": l.side,
            "price": float(l.price),
            "qty": float(l.qty),
            "usd_value": float(l.usd_value) if l.usd_value else None,
            "source": l.source,
            "timestamp": l.timestamp.isoformat(),
        } for l in liqs]

    cache_key = f"liquidations:{symbol or 'all'}:{limit}"
    return await get_cached_or_query(cache_key, 30, query)


async def get_liquidation_map(db: AsyncSession, symbol: str = "BTCUSDT", timeframe: str = "24h"):
    """C1: Enhanced liquidation map with timeframe support."""
    async def query():
        hours_map = {"1h": 1, "4h": 4, "24h": 24}
        hours = hours_map.get(timeframe, 24)

        stmt = (
            select(Liquidation)
            .where(Liquidation.symbol == symbol)
            .where(Liquidation.timestamp >= datetime.now(timezone.utc) - timedelta(hours=hours))
            .order_by(Liquidation.price)
        )
        result = await db.execute(stmt)
        liqs = result.scalars().all()

        if not liqs:
            return {
                "symbol": symbol, "timeframe": timeframe,
                "price_levels": [], "current_price": None,
                "total_long_liq": 0, "total_short_liq": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        prices = [float(l.price) for l in liqs]
        price_range = max(prices) - min(prices)
        bucket_size = max(price_range / 50, 50) if price_range > 0 else 100

        price_buckets: dict[float, dict] = {}
        total_long = 0.0
        total_short = 0.0

        for l in liqs:
            price = float(l.price)
            bucket = round(price / bucket_size) * bucket_size
            if bucket not in price_buckets:
                price_buckets[bucket] = {"long_liq": 0.0, "short_liq": 0.0, "count": 0}
            usd = float(l.usd_value or l.qty * l.price)
            if l.side == "LONG":
                price_buckets[bucket]["long_liq"] += usd
                total_long += usd
            else:
                price_buckets[bucket]["short_liq"] += usd
                total_short += usd
            price_buckets[bucket]["count"] += 1

        ticker_stmt = (
            select(MarketTicker.price)
            .where(MarketTicker.symbol == symbol)
            .order_by(desc(MarketTicker.timestamp))
            .limit(1)
        )
        current_price_row = await db.execute(ticker_stmt)
        current_price = float(current_price_row.scalar() or 0)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "total_long_liq": round(total_long, 2),
            "total_short_liq": round(total_short, 2),
            "price_levels": [
                {"price": price, "long_liq": round(data["long_liq"], 2),
                 "short_liq": round(data["short_liq"], 2), "count": data["count"]}
                for price, data in sorted(price_buckets.items())
            ],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    return await get_cached_or_query(f"liq_map:{symbol}:{timeframe}", 30, query)


async def get_orderbook(db: AsyncSession, symbol: str = "BTCUSDT"):
    async def query():
        stmt = (
            select(OrderbookSnapshot)
            .where(OrderbookSnapshot.symbol == symbol)
            .order_by(desc(OrderbookSnapshot.timestamp))
            .limit(1)
        )
        result = await db.execute(stmt)
        ob = result.scalar_one_or_none()
        if not ob:
            return {"symbol": symbol, "bids": [], "asks": [], "timestamp": None}

        bids = ob.bids or []
        asks = ob.asks or []
        total_bid_qty = sum(b[1] for b in bids) if bids else 0
        total_ask_qty = sum(a[1] for a in asks) if asks else 0
        bid_ask_ratio = (total_bid_qty / total_ask_qty) if total_ask_qty > 0 else 0

        avg_qty = (total_bid_qty + total_ask_qty) / max(len(bids) + len(asks), 1)
        whale_threshold = avg_qty * 3

        whale_bids = [b for b in bids if b[1] >= whale_threshold]
        whale_asks = [a for a in asks if a[1] >= whale_threshold]

        return {
            "symbol": ob.symbol,
            "bids": bids,
            "asks": asks,
            "source": ob.source,
            "timestamp": ob.timestamp.isoformat(),
            "bid_ask_ratio": round(bid_ask_ratio, 4),
            "total_bid_qty": round(total_bid_qty, 4),
            "total_ask_qty": round(total_ask_qty, 4),
            "whale_bids": whale_bids,
            "whale_asks": whale_asks,
        }

    return await get_cached_or_query(f"orderbook:{symbol}", 5, query)


async def get_open_interest_data(db: AsyncSession, symbol: Optional[str] = None, limit: int = 100):
    async def query():
        stmt = select(OpenInterest).order_by(desc(OpenInterest.timestamp)).limit(limit)
        if symbol:
            stmt = stmt.where(OpenInterest.symbol == symbol)
        result = await db.execute(stmt)
        ois = result.scalars().all()
        return [{
            "id": o.id,
            "symbol": o.symbol,
            "long_oi": float(o.long_oi),
            "short_oi": float(o.short_oi),
            "total_oi": float(o.long_oi + o.short_oi),
            "source": o.source,
            "timestamp": o.timestamp.isoformat(),
        } for o in ois]

    cache_key = f"oi:{symbol or 'all'}:{limit}"
    return await get_cached_or_query(cache_key, 60, query)


async def get_funding_rates(db: AsyncSession, symbol: Optional[str] = None, limit: int = 100):
    async def query():
        stmt = select(FundingRate).order_by(desc(FundingRate.timestamp)).limit(limit)
        if symbol:
            stmt = stmt.where(FundingRate.symbol == symbol)
        result = await db.execute(stmt)
        rates = result.scalars().all()
        return [{
            "symbol": r.symbol,
            "rate": float(r.rate),
            "source": r.source,
            "timestamp": r.timestamp.isoformat(),
        } for r in rates]

    cache_key = f"funding:{symbol or 'all'}:{limit}"
    return await get_cached_or_query(cache_key, 60, query)


async def get_market_overview(db: AsyncSession):
    async def query():
        stmt = text("""
            SELECT DISTINCT ON (symbol) symbol, price, price_change_24h,
                   volume_24h, high_24h, low_24h, source, timestamp
            FROM market_tickers
            ORDER BY symbol, timestamp DESC
        """)
        result = await db.execute(stmt)
        rows = result.fetchall()
        return [{
            "symbol": r[0],
            "price": float(r[1]) if r[1] else 0,
            "price_change_24h": float(r[2]) if r[2] else 0,
            "volume_24h": float(r[3]) if r[3] else 0,
            "high_24h": float(r[4]) if r[4] else 0,
            "low_24h": float(r[5]) if r[5] else 0,
            "source": r[6],
            "timestamp": r[7].isoformat() if r[7] else None,
        } for r in rows]

    return await get_cached_or_query("market_overview", 30, query)
