"""Job: Update stock universe."""

from src.data.universe_manager import update_universe
from src.utils.logger import logger


def run(data_source: str = "akshare"):
    """Fetch and save the latest stock universe.

    Args:
        data_source: "akshare", "tushare", or "auto"
    """
    logger.info(f"=== Updating stock universe (source: {data_source}) ===")
    df = update_universe(data_source=data_source)
    if df is not None:
        logger.info(f"Universe updated: {len(df)} stocks")
        return True
    logger.error("Universe update failed")
    return False


if __name__ == "__main__":
    run()
