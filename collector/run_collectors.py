import asyncio
import logging
import signal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from app.collectors.binance_collector import BinanceCollector
from app.collectors.hyperliquid_collector import HyperliquidCollector
from app.collectors.okx_collector import OKXCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("collector_runner")


async def main():
    binance = BinanceCollector()
    hyperliquid = HyperliquidCollector()
    okx = OKXCollector()

    collectors = [binance, hyperliquid, okx]
    tasks: list[asyncio.Task] = []

    def shutdown():
        logger.info("Shutdown signal received, cancelling tasks...")
        for c in collectors:
            c.running = False
        for task in tasks:
            task.cancel()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    logger.info("Starting all collectors - connecting to Singapore DB")
    logger.info(f"  Database: {os.environ.get('DATABASE_HOST')}:{os.environ.get('DATABASE_PORT')}")

    tasks = [
        asyncio.create_task(binance.start()),
        asyncio.create_task(hyperliquid.start()),
        asyncio.create_task(okx.start()),
    ]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    finally:
        for c in collectors:
            try:
                await c.stop()
            except Exception as e:
                logger.error(f"Error stopping collector: {e}")
        logger.info("All collectors stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
