import argparse
import sys
import traceback

import config
from src.utils.logger import setup_logger, timed

logger = setup_logger("main")


@timed
def run_tracking_cycle():
    from src.utils.market_hours import is_market_open
    from src.data.cafef_fetcher import CafefFetcher
    from src.data.price_history import save_daily_prices
    from src.data.volume_history import detect_volume_spikes
    from src.data.watchlist import get_all_watched_symbols
    from src.analysis.profit_calculator import calculate_profits, filter_by_volume, generate_summary, _format_volume
    from src.analysis.ceiling_floor import detect_ceiling_floor
    from src.notifications.telegram_bot import TelegramNotifier

    logger.info("=== Starting tracking cycle ===")

    if not is_market_open():
        logger.info("Market is closed, skipping cycle")
        return

    # 1. Fetch all prices
    fetcher = CafefFetcher()
    price_df = fetcher.fetch_all()

    if price_df.empty:
        logger.warning("No price data fetched")
        return

    # 2. Calculate profits
    price_df = calculate_profits(price_df)

    # 3. Save volume history
    save_daily_prices(price_df)

    # 4. Top volume alert
    filtered = filter_by_volume(price_df, top_n=config.TOP_VOLUME_COUNT)
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)

    if not filtered.empty:
        messages = generate_summary(filtered)
        notifier.send_alert(messages)

    # 5. Ceiling/Floor alerts
    ceiling, floor = detect_ceiling_floor(price_df.copy())
    cf_lines = []
    if not ceiling.empty:
        cf_lines.append(f"<b>🔴 {len(ceiling)} MA CHAM TRAN</b>\n")
        for _, row in ceiling.head(15).iterrows():
            vol = _format_volume(row["volume"])
            cf_lines.append(f"<b>{row['symbol']}</b> | <code>{row['close']:,.0f}</code> | KL: {vol}")
    if not floor.empty:
        cf_lines.append(f"\n<b>🟢 {len(floor)} MA CHAM SAN</b>\n")
        for _, row in floor.head(15).iterrows():
            vol = _format_volume(row["volume"])
            cf_lines.append(f"<b>{row['symbol']}</b> | <code>{row['close']:,.0f}</code> | KL: {vol}")
    if cf_lines:
        notifier.send_message("\n".join(cf_lines), disable_preview=True)

    # 6. Volume spike alerts
    spikes = detect_volume_spikes(price_df.copy(), multiplier=config.VOLUME_SPIKE_MULTIPLIER)
    if not spikes.empty:
        spike_lines = [f"<b>⚡ DOT BIEN KHOI LUONG ({len(spikes)} ma)</b>\n"]
        for _, row in spikes.head(15).iterrows():
            sign = "+" if row["profit_pct"] >= 0 else ""
            vol = _format_volume(row["volume"])
            spike_lines.append(
                f"<b>{row['symbol']}</b> KL: {vol} "
                f"(<b>{row['volume_ratio']:.1f}x</b> TB) | {sign}{row['profit_pct']:.2f}%"
            )
        notifier.send_message("\n".join(spike_lines), disable_preview=True)

    # 7. Watchlist alerts
    watched = get_all_watched_symbols()
    if watched:
        for symbol, chat_ids in watched.items():
            match = price_df[price_df["symbol"] == symbol]
            if match.empty:
                continue
            row = match.iloc[0]
            pct = row.get("profit_pct", 0)
            if abs(pct) < config.WATCHLIST_ALERT_PCT:
                continue
            sign = "+" if pct >= 0 else ""
            vol = _format_volume(row["volume"])
            text = (
                f"<b>🔔 WATCHLIST: {symbol}</b>\n"
                f"Gia: <code>{row['close']:,.0f}</code> ({sign}{pct:.2f}%)\n"
                f"KL: {vol}"
            )
            for cid in chat_ids:
                n = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, cid)
                n.send_message(text, disable_preview=True)

    logger.info(f"=== Cycle complete ===")


@timed
def run_test_cycle():
    from src.data.cafef_fetcher import CafefFetcher
    from src.analysis.profit_calculator import calculate_profits, filter_by_volume, generate_summary
    from src.notifications.telegram_bot import TelegramNotifier

    logger.info("=== Starting TEST cycle (no market hours check) ===")

    fetcher = CafefFetcher()
    price_df = fetcher.fetch_all()

    if price_df.empty:
        notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        notifier.send_message("[TEST] Khong co du lieu gia hom nay.")
        logger.info("No data, sent test message")
        return

    price_df = calculate_profits(price_df)
    filtered = filter_by_volume(price_df, top_n=config.TOP_VOLUME_COUNT)

    messages = generate_summary(filtered)
    messages[0] = "[TEST] " + messages[0]
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    notifier.send_alert(messages)

    logger.info(f"=== Test cycle complete: {len(filtered)} symbols alerted ===")


@timed
def run_daily_report():
    from src.data.cafef_fetcher import CafefFetcher
    from src.analysis.profit_calculator import calculate_profits
    from src.data.volume_history import save_daily_volumes
    from src.analysis.daily_report import generate_daily_report
    from src.notifications.telegram_bot import TelegramNotifier

    logger.info("=== Generating daily report ===")

    fetcher = CafefFetcher()
    price_df = fetcher.fetch_all()

    if price_df.empty:
        logger.warning("No price data for report")
        return

    price_df = calculate_profits(price_df)
    save_daily_prices(price_df)

    messages = generate_daily_report(price_df)
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    notifier.send_alert(messages)

    logger.info("=== Daily report sent ===")


def main():
    parser = argparse.ArgumentParser(description="Vietnam Stock Tracker")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--setup", action="store_true", help="Setup Telegram bot via QR code")
    parser.add_argument("--test", action="store_true", help="Fetch data and send Telegram (ignore market hours)")
    parser.add_argument("--report", action="store_true", help="Generate and send daily report now")
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

    # Test mode
    if args.test:
        logger.info("Running test cycle (ignoring market hours)")
        run_test_cycle()
        return

    # Manual report
    if args.report:
        run_daily_report()
        return

    # Single cycle
    if args.once:
        logger.info("Running single cycle (--once)")
        run_tracking_cycle()
        return

    # Scheduled mode with command bot
    from apscheduler.schedulers.blocking import BlockingScheduler
    from src.notifications.telegram_commands import TelegramCommandBot

    # Start command bot (polling in background thread)
    cmd_bot = TelegramCommandBot(config.TELEGRAM_BOT_TOKEN)
    cmd_bot.start_polling()

    # Scheduler
    scheduler = BlockingScheduler(timezone="Asia/Ho_Chi_Minh")

    # Tracking cycle every N minutes
    scheduler.add_job(
        run_tracking_cycle,
        "interval",
        minutes=config.SCHEDULE_INTERVAL_MINUTES,
        misfire_grace_time=60,
        id="tracking",
    )

    # Daily report at 15:05 (after market close at 15:00)
    scheduler.add_job(
        run_daily_report,
        "cron",
        hour=15,
        minute=5,
        day_of_week="mon-fri",
        id="daily_report",
    )

    logger.info(
        f"Starting scheduler: tracking every {config.SCHEDULE_INTERVAL_MINUTES}min, "
        f"daily report at 15:05, command bot active"
    )

    try:
        run_tracking_cycle()
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        cmd_bot.stop_polling()
        logger.info("Scheduler stopped")
    except Exception:
        logger.error(f"Fatal error:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
