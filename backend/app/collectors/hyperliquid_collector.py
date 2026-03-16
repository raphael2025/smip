import asyncio
import json
import logging
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import aiohttp
from sqlalchemy import insert, update, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import get_settings
from app.models import Trader, Trade

logger = logging.getLogger("hyperliquid_collector")
settings = get_settings()

HL_API = "https://api.hyperliquid.xyz"
MAX_TRACKED_WALLETS = 2000


class LRUWalletSet:
    """LRU-evicting wallet tracker with a hard capacity limit."""

    def __init__(self, maxsize: int = MAX_TRACKED_WALLETS):
        self._data: OrderedDict[str, datetime] = OrderedDict()
        self._maxsize = maxsize

    def add(self, wallet: str):
        if wallet in self._data:
            self._data.move_to_end(wallet)
        else:
            if len(self._data) >= self._maxsize:
                self._data.popitem(last=False)
            self._data[wallet] = datetime.now(timezone.utc)

    def __contains__(self, wallet: str) -> bool:
        return wallet in self._data

    def __len__(self) -> int:
        return len(self._data)

    def snapshot(self, limit: int = 500) -> list:
        return list(self._data.keys())[-limit:]


class HyperliquidCollector:
    def __init__(self):
        self.engine = create_async_engine(settings.database_url, pool_size=10)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.running = False
        self.tracked_wallets = LRUWalletSet(MAX_TRACKED_WALLETS)

    async def start(self):
        self.running = True
        logger.info("Starting Hyperliquid collector")
        await asyncio.gather(
            self._discover_traders(),
            self._poll_trader_fills(),
            self._poll_trader_positions(),
        )

    async def stop(self):
        self.running = False
        await self.engine.dispose()

    async def _discover_traders(self):
        while self.running:
            try:
                async with aiohttp.ClientSession() as http:
                    for coin in ["BTC", "ETH", "SOL"]:
                        payload = {"type": "recentTrades", "coin": coin}
                        async with http.post(f"{HL_API}/info", json=payload) as resp:
                            if resp.status == 200:
                                trades = await resp.json()
                                for t in trades:
                                    addr = t.get("users", [None, None])
                                    if isinstance(addr, list):
                                        for a in addr:
                                            if a and a not in self.tracked_wallets:
                                                self.tracked_wallets.add(a)
                                                await self._upsert_trader(a)
                        await asyncio.sleep(1)
                logger.info(f"Tracking {len(self.tracked_wallets)} wallets (max {MAX_TRACKED_WALLETS})")
            except Exception as e:
                logger.error(f"Discover traders error: {e}")
            await asyncio.sleep(120)

    async def _upsert_trader(self, wallet: str):
        try:
            async with self.session_factory() as session:
                stmt = pg_insert(Trader).values(
                    wallet_address=wallet,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=["wallet_address"])
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"Upsert trader error: {e}")

    async def _poll_trader_fills(self):
        while self.running:
            try:
                wallets = self.tracked_wallets.snapshot(500)
                async with aiohttp.ClientSession() as http:
                    for wallet in wallets:
                        if not self.running:
                            break
                        try:
                            payload = {"type": "userFills", "user": wallet}
                            async with http.post(f"{HL_API}/info", json=payload) as resp:
                                if resp.status == 200:
                                    fills = await resp.json()
                                    await self._process_fills(wallet, fills)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Fill poll error for {wallet}: {e}")
            except Exception as e:
                logger.error(f"Fill poll loop error: {e}")
            await asyncio.sleep(60)

    async def _process_fills(self, wallet: str, fills: list):
        if not fills:
            return
        try:
            async with self.session_factory() as session:
                for fill in fills[-50:]:
                    coin = fill.get("coin", "")
                    symbol = f"{coin}-PERP"
                    side = "LONG" if fill.get("side") == "B" else "SHORT"
                    size = Decimal(str(fill.get("sz", 0)))
                    price = Decimal(str(fill.get("px", 0)))
                    pnl = Decimal(str(fill.get("closedPnl", 0)))
                    ts = datetime.fromtimestamp(
                        fill.get("time", 0) / 1000, tz=timezone.utc
                    )

                    stmt = pg_insert(Trade).values(
                        wallet_address=wallet,
                        symbol=symbol,
                        side=side,
                        size=size,
                        entry_price=price,
                        pnl=pnl if pnl != 0 else None,
                        open_time=ts,
                        is_closed=pnl != 0,
                        close_time=ts if pnl != 0 else None,
                        source="hyperliquid",
                    ).on_conflict_do_nothing(
                        index_elements=["wallet_address", "symbol", "side", "entry_price", "open_time", "source"]
                    )
                    await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"Process fills error: {e}")

    async def _poll_trader_positions(self):
        while self.running:
            try:
                wallets = self.tracked_wallets.snapshot(200)
                async with aiohttp.ClientSession() as http:
                    for wallet in wallets:
                        if not self.running:
                            break
                        try:
                            payload = {"type": "clearinghouseState", "user": wallet}
                            async with http.post(f"{HL_API}/info", json=payload) as resp:
                                if resp.status == 200:
                                    state = await resp.json()
                                    await self._update_trader_metrics(wallet, state)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Position poll error for {wallet}: {e}")
            except Exception as e:
                logger.error(f"Position poll loop error: {e}")
            await asyncio.sleep(300)

    async def _update_trader_metrics(self, wallet: str, state: dict):
        try:
            async with self.session_factory() as session:
                total_stmt = select(func.count()).where(Trade.wallet_address == wallet)
                win_stmt = select(func.count()).where(
                    Trade.wallet_address == wallet,
                    Trade.pnl > 0,
                    Trade.is_closed == True,
                )
                pnl_stmt = select(func.sum(Trade.pnl)).where(
                    Trade.wallet_address == wallet,
                    Trade.is_closed == True,
                )
                gross_profit_stmt = select(func.sum(Trade.pnl)).where(
                    Trade.wallet_address == wallet,
                    Trade.is_closed == True,
                    Trade.pnl > 0,
                )
                gross_loss_stmt = select(func.sum(Trade.pnl)).where(
                    Trade.wallet_address == wallet,
                    Trade.is_closed == True,
                    Trade.pnl < 0,
                )

                total_count = (await session.execute(total_stmt)).scalar() or 0
                win_count = (await session.execute(win_stmt)).scalar() or 0
                total_pnl = (await session.execute(pnl_stmt)).scalar() or Decimal(0)
                gross_profit = (await session.execute(gross_profit_stmt)).scalar() or Decimal(0)
                gross_loss_raw = (await session.execute(gross_loss_stmt)).scalar() or Decimal(0)
                gross_loss = abs(gross_loss_raw)

                win_rate = (win_count / total_count * 100) if total_count > 0 else 0

                # B2: Real profit factor
                if gross_loss > 0:
                    profit_factor = float(gross_profit) / float(gross_loss)
                else:
                    profit_factor = 999.0 if gross_profit > 0 else 0.0

                # B1: Real max drawdown (cumulative PnL peak-to-trough)
                max_drawdown = await self._calc_max_drawdown(session, wallet)

                # B3: Real scoring formula
                is_smart = (
                    total_count > 30
                    and win_rate > 55
                    and float(total_pnl) > 0
                    and max_drawdown < 30
                )

                score = (
                    0.20 * min(win_rate / 100, 1.0)
                    + 0.30 * min(max(float(total_pnl) / 10000, 0), 1.0)
                    + 0.20 * max(1.0 - max_drawdown / 100, 0)
                    + 0.15 * min(profit_factor / 5.0, 1.0)
                    + 0.15 * min(total_count / 200, 1.0)
                )

                last_trade_stmt = (
                    select(Trade.open_time)
                    .where(Trade.wallet_address == wallet)
                    .order_by(Trade.open_time.desc())
                    .limit(1)
                )
                last_trade_time = (await session.execute(last_trade_stmt)).scalar()

                stmt = (
                    update(Trader)
                    .where(Trader.wallet_address == wallet)
                    .values(
                        total_pnl=total_pnl,
                        win_rate=Decimal(str(round(win_rate, 2))),
                        trade_count=total_count,
                        max_drawdown=Decimal(str(round(max_drawdown, 2))),
                        profit_factor=Decimal(str(round(profit_factor, 4))),
                        score=Decimal(str(round(score, 4))),
                        is_smart_money=is_smart,
                        last_trade_time=last_trade_time,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            logger.error(f"Update metrics error for {wallet}: {e}")

    async def _calc_max_drawdown(self, session: AsyncSession, wallet: str) -> float:
        """Calculate max drawdown using cumulative PnL peak-to-trough method."""
        try:
            stmt = (
                select(Trade.pnl)
                .where(
                    Trade.wallet_address == wallet,
                    Trade.is_closed == True,
                    Trade.pnl.isnot(None),
                )
                .order_by(Trade.open_time)
            )
            result = await session.execute(stmt)
            pnls = [float(row[0]) for row in result.fetchall()]

            if not pnls:
                return 0.0

            cumulative = 0.0
            peak = 0.0
            max_dd = 0.0

            for pnl in pnls:
                cumulative += pnl
                peak = max(peak, cumulative)
                if peak > 0:
                    dd = (peak - cumulative) / peak * 100
                    max_dd = max(max_dd, dd)

            return min(max_dd, 100.0)
        except Exception as e:
            logger.error(f"Max drawdown calc error for {wallet}: {e}")
            return 0.0
