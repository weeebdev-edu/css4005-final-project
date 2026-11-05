"""Optional ClickHouse side-store: every write is also recorded as an event.

Enabled only when CLICKHOUSE_URL is set, e.g.
clickhouse://analytics:${PASSWORD}@clickhouse:8123/campus
Failures are logged and never break the main request.
"""

import logging
from datetime import UTC, datetime

log = logging.getLogger("campus.analytics")

DDL = """
CREATE TABLE IF NOT EXISTS events (
    ts       DateTime64(3, 'UTC'),
    action   LowCardinality(String),
    item_id  UInt64,
    owner    String
) ENGINE = MergeTree ORDER BY (ts, action)
"""


class Analytics:
    def __init__(self, url: str | None, owner: str):
        self.client = None
        self.owner = owner
        if not url:
            return
        try:
            import clickhouse_connect

            self.client = clickhouse_connect.get_client(dsn=url)
            self.client.command(DDL)
            log.info("clickhouse analytics enabled")
        except Exception as exc:  # analytics must never take the app down
            log.warning("clickhouse unavailable, analytics disabled: %s", type(exc).__name__)
            self.client = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def record(self, action: str, item_id: int) -> None:
        if not self.client:
            return
        try:
            self.client.insert(
                "events",
                [[datetime.now(UTC), action, item_id, self.owner]],
                column_names=["ts", "action", "item_id", "owner"],
            )
        except Exception as exc:
            log.warning("failed to record event: %s", type(exc).__name__)
