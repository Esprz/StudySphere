import os

KAFKA_CONFIG = {
    'bootstrap_servers': [
        os.getenv('KAFKA_BROKERS', 'kafka:9092')
    ],
    'client_id': 'studysphere',
    'auto_offset_reset': 'earliest',
    'enable_auto_commit': True,
    'group_id': 'studysphere-recommendation-system',
    'session_timeout_ms': 30000,
    'heartbeat_interval_ms': 3000,
}

PRODUCER_CONFIG = {
    **KAFKA_CONFIG,
    'acks': 'all',
    'retries': 3,
    'batch_size': 16384,
    'linger_ms': 10,
    'buffer_memory': 33554432,
}

CONSUMER_CONFIG = {
    **KAFKA_CONFIG,
    'fetch_min_bytes': 1,
    'fetch_max_wait_ms': 500,
    'max_partition_fetch_bytes': 1048576,
}