-- Initialize mesh_network database and tables

CREATE DATABASE IF NOT EXISTS mesh_network;

CREATE TABLE IF NOT EXISTS mesh_network.packets (
    timestamp DateTime64(3),
    message_id String,
    from_node String,
    to_node Nullable(String),
    payload_hash String,
    delivered UInt8,
    latency_ms Float64
) ENGINE = MergeTree()
ORDER BY (timestamp, from_node)
TTL toDateTime(timestamp) + INTERVAL 30 DAY;

-- Create a view for quick statistics
CREATE VIEW IF NOT EXISTS mesh_network.packet_stats AS
SELECT
    toStartOfHour(timestamp) AS hour,
    count() AS total_packets,
    countIf(delivered = 1) AS delivered_packets,
    countIf(delivered = 0) AS lost_packets,
    delivered_packets / total_packets AS pdr,
    avg(if(delivered = 1, latency_ms, null)) AS avg_latency_ms,
    quantile(0.95)(if(delivered = 1, latency_ms, null)) AS p95_latency_ms
FROM mesh_network.packets
GROUP BY hour
ORDER BY hour DESC;

