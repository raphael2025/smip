#!/usr/bin/env python3
"""B5: Batch recalculate all trader metrics after dedup cleanup."""
import asyncio
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'collector', '.env'), override=True)

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import get_settings
from app.models import Trader, Trade

settings = get_settings()


async def recalculate_all():
    engine = create_async_engine(settings.database_url, pool_size=5)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(Trader.wallet_address))
        wallets = [row[0] for row in result.fetchall()]

    print(f"Recalculating metrics for {len(wallets)} traders...")
    updated = 0
    errors = 0

    for i, wallet in enumerate(wallets):
        try:
            async with session_factory() as session:
                total_count = (await session.execute(
                    select(func.count()).where(Trade.wallet_address == wallet)
                )).scalar() or 0

                win_count = (await session.execute(
                    select(func.count()).where(
                        Trade.wallet_address == wallet,
                        Trade.pnl > 0,
                        Trade.is_closed == True,
                    )
                )).scalar() or 0

                total_pnl = (await session.execute(
                    select(func.sum(Trade.pnl)).where(
                        Trade.wallet_address == wallet,
                        Trade.is_closed == True,
                    )
                )).scalar() or Decimal(0)

                gross_profit = (await session.execute(
                    select(func.sum(Trade.pnl)).where(
                        Trade.wallet_address == wallet,
                        Trade.is_closed == True,
                        Trade.pnl > 0,
                    )
                )).scalar() or Decimal(0)

                gross_loss_raw = (await session.execute(
                    select(func.sum(Trade.pnl)).where(
                        Trade.wallet_address == wallet,
                        Trade.is_closed == True,
                        Trade.pnl < 0,
                    )
                )).scalar() or Decimal(0)
                gross_loss = abs(gross_loss_raw)

                win_rate = (win_count / total_count * 100) if total_count > 0 else 0.0

                if gross_loss > 0:
                    profit_factor = float(gross_profit) / float(gross_loss)
                else:
                    profit_factor = 999.0 if gross_profit > 0 else 0.0

                pnl_result = await session.execute(
                    select(Trade.pnl)
                    .where(
                        Trade.wallet_address == wallet,
                        Trade.is_closed == True,
                        Trade.pnl.isnot(None),
                    )
                    .order_by(Trade.open_time)
                )
                pnls = [float(row[0]) for row in pnl_result.fetchall()]

                max_drawdown = 0.0
                if pnls:
                    cumulative = 0.0
                    peak = 0.0
                    for pnl in pnls:
                        cumulative += pnl
                        peak = max(peak, cumulative)
                        if peak > 0:
                            dd = (peak - cumulative) / peak * 100
                            max_drawdown = max(max_drawdown, dd)
                    max_drawdown = min(max_drawdown, 100.0)

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

                last_trade_result = await session.execute(
                    select(Trade.open_time)
                    .where(Trade.wallet_address == wallet)
                    .order_by(Trade.open_time.desc())
                    .limit(1)
                )
                last_trade_time = last_trade_result.scalar()

                await session.execute(
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
                    )
                )
                await session.commit()
                updated += 1

        except Exception as e:
            errors += 1
            print(f"  Error for {wallet}: {e}")

        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{len(wallets)} (updated={updated}, errors={errors})")

    await engine.dispose()
    print(f"\nDone! Updated: {updated}, Errors: {errors}")


if __name__ == "__main__":
    asyncio.run(recalculate_all())
