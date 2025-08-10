export interface KafkaConfig {
    clientId: string;
    brokers: string[];
    connectionTimeout?: number;
    authenticationTimeout?: number;
    reauthenticationThreshold?: number;
    retry?: {
        initialRetryTime: number;
        retries: number;
    };
}

export interface TopicConfig {
    topic: string;
    partitions: number;
    replicationFactor: number;
    config?: Record<string, string>;
}

export interface TopicsConfig {
    USER_EVENTS: TopicConfig;
    POST_EVENTS: TopicConfig;
    BEHAVIOR_EVENTS: TopicConfig;
    //NOTIFICATIONS: TopicConfig;
}
