TOPICS_CONFIG = {
    'USER_BEHAVIOR': {
        'topic': 'user-behavior',
        'partitions': 3,
        'replication_factor': 1,
        'config': {
            'cleanup.policy': 'delete',
            'retention.ms': '604800000',  # 7 days
            'compression.type': 'snappy'
        }
    },
    'RECOMMENDATIONS': {
        'topic': 'recommendations',
        'partitions': 2,
        'replication_factor': 1,
        'config': {
            'cleanup.policy': 'delete',
            'retention.ms': '86400000',  # 1 day
            'compression.type': 'snappy'
        }
    },
    'NOTIFICATIONS': {
        'topic': 'notifications',
        'partitions': 2,
        'replication_factor': 1,
        'config': {
            'cleanup.policy': 'delete',
            'retention.ms': '259200000',  # 3 days
            'compression.type': 'snappy'
        }
    }
}

# 导出topic名称供快速访问
TOPIC_NAMES = {
    'USER_BEHAVIOR': TOPICS_CONFIG['USER_BEHAVIOR']['topic'],
    'RECOMMENDATIONS': TOPICS_CONFIG['RECOMMENDATIONS']['topic'],
    'NOTIFICATIONS': TOPICS_CONFIG['NOTIFICATIONS']['topic'],
}