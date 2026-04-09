import argparse
import sys
import traceback
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

import config
from src.utils.logger import setup_logger, timed
from src.utils.market_hours import is_market_open, VN_TZ
from src.data.symbol_manager import get_all_symbols
from src.data.vnstock_fetcher import VnstockFetcher
from src.data.yfinance_fetcher import YfinanceFetcher
from src.analysis.profit_calculator import calculate_profits, filter_profitable, generate_summary
from src.charting.chart_generator import generate_chart, cleanup_old_charts
from src.notifications.telegram_bot import TelegramNotifier

logger = setup_logger("main")


def get_fetcher():
    if config.DATA_SOURCE == "yfinance":
        return YfinanceFetcher()
    return VnstockFetcher()


@timed
def run_tracking_cycle():
    logger.info("=== Starting tracking cycle ===")

    # Check market hours
    if not is_market_open():
        logger.info("Market is closed, skipping cycle")
        return

    # 1. Get symbols
    symbols = get_all_symbols()
    if not symbols:
        logger.error("No symbols available, aborting cycle")
        return
    logger.info(f"Tracking {len(symbols)} symbols")

    # 2. Fetch prices
    now = datetime.now(VN_TZ)
    today = now.strftime("%Y-%m-%d")
    fetcher = get_fetcher()
    price_df = fetcher.fetch_batch(symbols, start=today, end=today)

    if price_df.empty:
        logger.warning("No price data fetched")
        return

    # 3. Calculate profits
    price_df = calculate_profits(price_df)
    filtered = filter_profitable(price_df, threshold=config.PROFIT_THRESHOLD)

    if filtered.empty:
        logger.info("No symbols above profit threshold")
        return

    # 4. Generate charts
    chart_paths = {}
    for _, row in filtered.head(config.MAX_TELEGRAM_SYMBOLS).iterrows():
        symbol = row["symbol"]
        sym_data = price_df[price_df["symbol"] == symbol]
        try:
            path = generate_chart(symbol, sym_data)
            chart_paths[symbol] = path
        except Exception as e:
            logger.warning(f"Chart generation failed for {symbol}: {e}")

    # 5. Send Telegram alerts
    summary = generate_summary(filtered)
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    notifier.send_alert_batch(summary, chart_paths, max_symbols=config.MAX_TELEGRAM_SYMBOLS)

    # Cleanup old charts
    cleanup_old_charts()

    logger.info(f"=== Cycle complete: {len(filtered)} symbols alerted ===")


def main():
    parser = argparse.ArgumentParser(description="Vietnam Stock Tracker")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--setup", action="store_true", help="Setup Telegram bot via QR code")
    args = parser.parse_args()

    # Telegram setup mode
    if args.setup:
        from src.notifications.telegram_setup import run_setup
        token = config.TELEGRAM_BOT_TOKEN if config.TELEGRAM_BOT_TOKEN != "your_bot_token_here" else None
        success = run_setup(token)
        sys.exit(0 if success else 1)

    # Validate config
    errors = config.validate()
    if errors:
        for e in errors:
            logger.error(f"Config error: {e}")
        sys.exit(1)

    if args.once:
        logger.info("Running single cycle (--once)")
        run_tracking_cycle()
        return

    # Scheduled mode
    logger.info(f"Starting scheduler: every {config.SCHEDULE_INTERVAL_MINUTES} minutes")
    scheduler = BlockingScheduler(timezone="Asia/Ho_Chi_Minh")
    scheduler.add_job(
        run_tracking_cycle,
        "interval",
        minutes=config.SCHEDULE_INTERVAL_MINUTES,
        misfire_grace_time=60,
    )

    try:
        # Run once immediately, then schedule
        run_tracking_cycle()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
    except Exception:
        logger.error(f"Fatal error:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
