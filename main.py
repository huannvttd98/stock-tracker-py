import argparse
import sys
import traceback
from datetime import datetime, timedelta, timezone

import config
from src.utils.logger import setup_logger, timed

logger = setup_logger("main")


def get_fetcher():
    if config.DATA_SOURCE == "yfinance":
        from src.data.yfinance_fetcher import YfinanceFetcher
        return YfinanceFetcher()
    from src.data.vnstock_fetcher import VnstockFetcher
    return VnstockFetcher()


@timed
def run_tracking_cycle():
    from src.utils.market_hours import is_market_open, VN_TZ
    from src.data.symbol_manager import get_all_symbols
    from src.analysis.profit_calculator import calculate_profits, filter_by_volume, generate_summary
    from src.notifications.telegram_bot import TelegramNotifier

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
    filtered = filter_by_volume(price_df, top_n=config.TOP_VOLUME_COUNT)

    if filtered.empty:
        logger.info("No symbols above volume threshold")
        return

    # 4. Send Telegram alerts
    messages = generate_summary(filtered)
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    notifier.send_alert(messages)

    logger.info(f"=== Cycle complete: {len(filtered)} symbols alerted ===")


@timed
def run_test_cycle():
    from src.utils.market_hours import VN_TZ
    from src.data.symbol_manager import get_all_symbols
    from src.analysis.profit_calculator import calculate_profits, filter_by_volume, generate_summary
    from src.notifications.telegram_bot import TelegramNotifier

    logger.info("=== Starting TEST cycle (no market hours check) ===")

    symbols = get_all_symbols()
    if not symbols:
        logger.error("No symbols available, aborting")
        return

    logger.info(f"Tracking {len(symbols)} symbols")

    now = datetime.now(VN_TZ)
    today = now.strftime("%Y-%m-%d")
    fetcher = get_fetcher()
    price_df = fetcher.fetch_batch(symbols, start=today, end=today)

    if price_df.empty:
        logger.warning("No price data fetched")
        return

    price_df = calculate_profits(price_df)
    filtered = filter_by_volume(price_df, top_n=config.TOP_VOLUME_COUNT)

    if filtered.empty:
        notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        notifier.send_message("[TEST] Khong co du lieu gia hom nay.")
        logger.info("No symbols above threshold, sent test message")
        return

    messages = generate_summary(filtered)
    messages[0] = "[TEST] " + messages[0]
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    notifier.send_alert(messages)

    logger.info(f"=== Test cycle complete: {len(filtered)} symbols alerted ===")


@timed
def run_report():
    from src.utils.market_hours import VN_TZ
    from src.data.symbol_manager import get_all_symbols
    from src.analysis.profit_calculator import calculate_profits, filter_profitable
    from src.report.html_report import generate_html_report
    import webbrowser
    import os

    logger.info("=== Generating HTML report ===")

    symbols = get_all_symbols()
    if not symbols:
        logger.error("No symbols available")
        return

    logger.info(f"Fetching data for {len(symbols)} symbols...")
    now = datetime.now(VN_TZ)
    today = now.strftime("%Y-%m-%d")
    fetcher = get_fetcher()
    price_df = fetcher.fetch_batch(symbols, start=today, end=today)

    if price_df.empty:
        logger.warning("No price data fetched")
        return

    price_df = calculate_profits(price_df)
    filtered = filter_by_volume(price_df, top_n=config.TOP_VOLUME_COUNT)

    report_path = generate_html_report(price_df, filtered)
    logger.info(f"Report saved: {report_path}")

    # Auto-open in browser
    webbrowser.open(f"file:///{os.path.abspath(report_path)}")
    print(f"\nReport: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Vietnam Stock Tracker")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--setup", action="store_true", help="Setup Telegram bot via QR code")
    parser.add_argument("--report", action="store_true", help="Fetch data and generate HTML report")
    parser.add_argument("--test", action="store_true", help="Fetch data and send Telegram (ignore market hours)")
    args = parser.parse_args()

    # Telegram setup mode
    if args.setup:
        from src.notifications.telegram_setup import run_setup
        token = config.TELEGRAM_BOT_TOKEN if config.TELEGRAM_BOT_TOKEN != "your_bot_token_here" else None
        success = run_setup(token)
        sys.exit(0 if success else 1)

    # Report mode - no Telegram needed
    if args.report:
        run_report()
        return

    # Validate config
    errors = config.validate()
    if errors:
        for e in errors:
            logger.error(f"Config error: {e}")
        sys.exit(1)

    # Test mode - fetch + send Telegram, ignore market hours
    if args.test:
        logger.info("Running test cycle (ignoring market hours)")
        run_test_cycle()
        return

    if args.once:
        logger.info("Running single cycle (--once)")
        run_tracking_cycle()
        return

    # Scheduled mode
    from apscheduler.schedulers.blocking import BlockingScheduler
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
