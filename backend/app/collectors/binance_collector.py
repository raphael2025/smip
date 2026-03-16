import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
import aiohttp
import websockets
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import get_settings
from app.models import Liquidation, OrderbookSnapshot, OpenInterest, FundingRate, MarketTicker

logger = logging.getLogger("binance_collector")
settings = get_settings()

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT"]

FUTURES_WS_BASE = "wss://fstream.binance.com"
FUTURES_API_BASE = "https://fapi.binance.com"


class BinanceCollector:
    def __init__(self):
        self.engine = create_async_engine(settings.database_url, pool_size=10)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Starting Binance collector")
        await asyncio.gather(
            self._collect_liquidations(),
            self._collect_orderbook(),
            self._poll_open_interest(),
            self._poll_funding_rates(),
            self._poll_tickers(),
        )

    async def stop(self):
        self.running = False
        await self.engine.dispose()

    async def _collect_liquidations(self):
        url = f"{FUTURES_WS_BASE}/ws/!forceOrder@arr"
        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    logger.info("Connected to Binance liquidation stream")
                    async for msg in ws:
                        if not self.running:
                            break
                        data = json.loads(msg)
                        await self._process_liquidation(data)
            except Exception as e:
                logger.error(f"Liquidation stream error: {e}")
                await asyncio.sleep(5)

    async def _process_liquidation(self, data: dict):
        try:
            o = data.get("o", data)
            symbol = o.get("s", "")
            if symbol not in SYMBOLS:
                return

            side = "LONG" if o.get("S") == "SELL" else "SHORT"
            price = Decimal(str(o.get("p", 0)))
            qty = Decimal(str(o.get("q", 0)))
            usd_value = price * qty
            ts = datetime.fromtimestamp(o.get("T", 0) / 1000, tz=timezone.utc)

            async with self.session_factory() as session:
                stmt = pg_insert(Liquidation).values(
                    symbol=symbol, side=side, price=price,
                    qty=qty, usd_value=usd_value,
                    source="binance", timestamp=ts
                ).on_conflict_do_nothing(
                    index_elements=["symbol", "side", "price", "qty", "timestamp", "source"]
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"Process liquidation error: {e}")

    async def _collect_orderbook(self):
        streams = "/".join([f"{s.lower()}@depth20@100ms" for s in SYMBOLS[:5]])
        url = f"{FUTURES_WS_BASE}/stream?streams={streams}"

        while self.running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    logger.info("Connected to Binance orderbook stream")
                    batch_count = 0
                    async for msg in ws:
                        if not self.running:
                            break
                        batch_count += 1
                        if batch_count % 50 == 0:
                            data = json.loads(msg)
                            await self._process_orderbook(data)
            except Exception as e:
                logger.error(f"Orderbook stream error: {e}")
                await asyncio.sleep(5)

    async def _process_orderbook(self, data: dict):
        try:
            stream = data.get("stream", "")
            symbol = stream.split("@")[0].upper()
            ob = data.get("data", {})

            bids = [[float(p), float(q)] for p, q in ob.get("b", [])[:20]]
            asks = [[float(p), float(q)] for p, q in ob.get("a", [])[:20]]

            async with self.session_factory() as session:
                from sqlalchemy import insert
                stmt = insert(OrderbookSnapshot).values(
                    symbol=symbol, bids=bids, asks=asks,
                    source="binance",
                    timestamp=datetime.now(timezone.utc)
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"Process orderbook error: {e}")

    async def _poll_open_interest(self):
        """B4: Fetch real OI + long/short ratio from Binance."""
        while self.running:
            try:
                async with aiohttp.ClientSession() as http:
                    for symbol in SYMBOLS:
                        try:
                            oi_url = f"{FUTURES_API_BASE}/fapi/v1/openInterest?symbol={symbol}"
                            async with http.get(oi_url) as resp:
                                if resp.status != 200:
                                    continue
                                oi_data = await resp.json()
                                total_oi = Decimal(str(oi_data.get("openInterest", 0)))

                            long_ratio = Decimal("0.5")
                            try:
                                ratio_url = f"{FUTURES_API_BASE}/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=5m&limit=1"
                                async with http.get(ratio_url) as ratio_resp:
                                    if ratio_resp.status == 200:
                                        ratio_data = await ratio_resp.json()
                                        if ratio_data:
                                            long_ratio = Decimal(str(ratio_data[0].get("longAccount", "0.5")))
                            except Exception:
                                pass

                            short_ratio = Decimal("1") - long_ratio
                            async with self.session_factory() as session:
                                from sqlalchemy import insert
                                stmt = insert(OpenInterest).values(
                                    symbol=symbol,
                                    long_oi=total_oi * long_ratio,
                                    short_oi=total_oi * short_ratio,
                                    source="binance",
                                    timestamp=datetime.now(timezone.utc)
                                )
                                await session.execute(stmt)
                                await session.commit()
                        except Exception as e:
                            logger.error(f"OI poll error for {symbol}: {e}")
                        await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"OI poll loop error: {e}")
            await asyncio.sleep(60)

    async def _poll_funding_rates(self):
        while self.running:
            try:
                async with aiohttp.ClientSession() as http:
                    url = f"{FUTURES_API_BASE}/fapi/v1/premiumIndex"
                    async with http.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            async with self.session_factory() as session:
                                from sqlalchemy import insert
                                for item in data:
                                    if item["symbol"] in SYMBOLS:
                                        stmt = insert(FundingRate).values(
                                            symbol=item["symbol"],
                                            rate=Decimal(str(item.get("lastFundingRate", 0))),
                                            source="binance",
                                            timestamp=datetime.now(timezone.utc)
                                        )
                                        await session.execute(stmt)
                                await session.commit()
            except Exception as e:
                logger.error(f"Funding rate poll error: {e}")
            await asyncio.sleep(300)

    async def _poll_tickers(self):
        while self.running:
            try:
                async with aiohttp.ClientSession() as http:
                    url = f"{FUTURES_API_BASE}/fapi/v1/ticker/24hr"
                    async with http.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            async with self.session_factory() as session:
                                from sqlalchemy import insert
                                for item in data:
                                    if item["symbol"] in SYMBOLS:
                                        stmt = insert(MarketTicker).values(
                                            symbol=item["symbol"],
                                            price=Decimal(str(item.get("lastPrice", 0))),
                                            price_change_24h=Decimal(str(item.get("priceChangePercent", 0))),
                                            volume_24h=Decimal(str(item.get("quoteVolume", 0))),
                                            high_24h=Decimal(str(item.get("highPrice", 0))),
                                            low_24h=Decimal(str(item.get("lowPrice", 0))),
                                            source="binance",
                                            timestamp=datetime.now(timezone.utc)
                                        )
                                        await session.execute(stmt)
                                await session.commit()
            except Exception as e:
                logger.error(f"Ticker poll error: {e}")
            await asyncio.sleep(30)
