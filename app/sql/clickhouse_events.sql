-- ClickHouse analytics side-store (the app also creates this table itself).
CREATE TABLE IF NOT EXISTS campus.events (
    ts       DateTime64(3, 'UTC'),
    action   LowCardinality(String),
    item_id  UInt64,
    owner    String
) ENGINE = MergeTree ORDER BY (ts, action);

-- EXAMPLE roles: the app may only insert, analysts may only read.
-- CREATE USER analytics IDENTIFIED WITH sha256_password BY '...';
-- CREATE USER analyst   IDENTIFIED WITH sha256_password BY '...';
-- GRANT CREATE TABLE, INSERT, SELECT ON campus.events TO analytics;
-- GRANT SELECT ON campus.events TO analyst;

-- Useful query for your dashboard / report:
-- SELECT toStartOfHour(ts) AS hour, action, count() FROM campus.events GROUP BY hour, action ORDER BY hour;
