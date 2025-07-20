module.exports = {
  USER_EVENTS: {
    topic: "user-events",
    partitions: 2,
    replicationFactor: 1,
    config: {
      "cleanup.policy": "delete",
      "retention.ms": "604800000", // 7 days
      "compression.type": "snappy",
    },
  },
  POST_EVENTS: {
    topic: "post-events",
    partitions: 3,
    replicationFactor: 1,
    config: {
      "cleanup.policy": "delete",
      "retention.ms": "604800000", // 7 days
      "compression.type": "snappy",
    },
  },
  BEHAVIOR_EVENTS: {
    topic: "behavior-events",
    partitions: 3,
    replicationFactor: 1,
    config: {
      "cleanup.policy": "delete",
      "retention.ms": "259200000", // 3 days
      "compression.type": "snappy",
    },
  },
  /*
    NOTIFICATIONS: {
        topic: 'notifications',
        partitions: 2,
        replicationFactor: 1,
        config: {
            'cleanup.policy': 'delete',
            'retention.ms': '86400000', // 1 day
            'compression.type': 'snappy'
        }
    }*/
};
