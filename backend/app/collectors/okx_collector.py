import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
import aiohttp
import websockets
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import get_settings
from app.models import Liquidation, OpenInterest, FundingRate, MarketTicker

logger = logging.getLogger("okx_collector")
settings = get_settings()

SYMBOLS_MAP = {
    "BTC-USDT-SWAP": "BTCUSDT",
    "ETH-USDT-SWAP": "ETHUSDT",
    "SOL-USDT-SWAP": "SOLUSDT",
    "DOGE-USDT-SWAP": "DOGEUSDT",
    "XRP-USDT-SWAP": "XRPUSDT",
}

OKX_WS = "wss://ws.okx.com:8443/ws/v5/public"
OKX_API = "https://www.okx.com"


class OKXCollector:
    def __init__(self):
        self.engine = create_async_engine(settings.database_url, pool_size=5)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Starting OKX collector")
        await asyncio.gather(
            self._collect_liquidations(),
            self._poll_tickers(),
            self._poll_funding_rates(),
        )

    async def stop(self):
        self.running = False
        await self.engine.dispose()

    async def _collect_liquidations(self):
        while self.running:
            try:
                async with websockets.connect(OKX_WS, ping_interval=20) as ws:
                    subscribe_msg = {
                        "op": "subscribe",
                        "args": [{"channel": "liquidation-orders", "instType": "SWAP"}]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info("Connected to OKX liquidation stream")

                    async for msg in ws:
                        if not self.running:
                            break
                        data = json.loads(msg)
                        if "data" in data:
                            for item in data["data"]:
                                await self._process_liquidation(item)
            except Exception as e:
                logger.error(f"OKX liquidation stream error: {e}")
                await asyncio.sleep(5)

    async def _process_liquidation(self, item: dict):
        try:
            inst_id = item.get("instId", "")
            mapped_symbol = SYMBOLS_MAP.get(inst_id)
            if not mapped_symbol:
                return

            details = item.get("details", [{}])
            for d in details:
                side = "LONG" if d.get("side") == "sell" else "SHORT"
                price = Decimal(str(d.get("bkPx", 0)))
                qty = Decimal(str(d.get("sz", 0)))
                ts_raw = d.get("ts")
                ts = datetime.fromtimestamp(int(ts_raw) / 1000, tz=timezone.utc) if ts_raw else datetime.now(timezone.utc)

                async with self.session_factory() as session:
                    stmt = pg_insert(Liquidation).values(
                        symbol=mapped_symbol,
                        side=side,
                        price=price,
                        qty=qty,
                        usd_value=price * qty,
                        source="okx",
                        timestamp=ts
                    ).on_conflict_do_nothing(
                        index_elements=["symbol", "side", "price", "qty", "timestamp", "source"]
                    )
                    await session.execute(stmt)
                    await session.commit()
        except Exception as e:
            logger.error(f"OKX process liquidation error: {e}")

    async def _poll_tickers(self):
        while self.running:
            try:
                async with aiohttp.ClientSession() as http:
                    url = f"{OKX_API}/api/v5/market/tickers?instType=SWAP"
                    async with http.get(url) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            data = result.get("data", [])
                            async with self.session_factory() as session:
                                for item in data:
                                    inst_id = item.get("instId", "")
                                    mapped = SYMBOLS_MAP.get(inst_id)
                                    if not mapped:
                                        continue
                                    open_24h = float(item.get("open24h", 0) or 1)
                                    last = float(item.get("last", 0) or 0)
                                    change_pct = ((last / open_24h) - 1) * 100 if open_24h else 0
                                    stmt = insert(MarketTicker).values(
                                        symbol=mapped,
                                        price=Decimal(str(last)),
                                        price_change_24h=Decimal(str(round(change_pct, 4))),
                                        volume_24h=Decimal(str(item.get("volCcy24h", 0) or 0)),
                                        high_24h=Decimal(str(item.get("high24h", 0) or 0)),
                                        low_24h=Decimal(str(item.get("low24h", 0) or 0)),
                                        source="okx",
                                        timestamp=datetime.now(timezone.utc)
                                    )
                                    await session.execute(stmt)
                                await session.commit()
            except Exception as e:
                logger.error(f"OKX ticker poll error: {e}")
            await asyncio.sleep(30)

    async def _poll_funding_rates(self):
        while self.running:
            try:
                async with aiohttp.ClientSession() as http:
                    for inst_id, mapped in SYMBOLS_MAP.items():
                        url = f"{OKX_API}/api/v5/public/funding-rate?instId={inst_id}"
                        async with http.get(url) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                data = result.get("data", [{}])
                                if data:
                                    rate = Decimal(str(data[0].get("fundingRate", 0)))
                                    async with self.session_factory() as session:
                                        stmt = insert(FundingRate).values(
                                            symbol=mapped,
                                            rate=rate,
                                            source="okx",
                                            timestamp=datetime.now(timezone.utc)
                                        )
                                        await session.execute(stmt)
                                        await session.commit()
                        await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"OKX funding rate poll error: {e}")
            await asyncio.sleep(300)
