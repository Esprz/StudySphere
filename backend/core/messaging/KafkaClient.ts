import { Kafka, Producer, Consumer } from 'kafkajs';
import { kafkaConfig, topicConfigs } from '../../config/kafka';
import { KafkaConfig, TopicsConfig } from '../../config/kafka_config_type';

class KafkaClient {
    private static instance: KafkaClient;
    private kafka: Kafka;
    private producer: Producer | null = null;
    private consumer: Consumer | null = null;
    private readonly config: KafkaConfig;
    private readonly topics: TopicsConfig;
    private isAvailable: boolean = false;

    private constructor() {
        this.config = kafkaConfig;
        this.topics = topicConfigs;
        this.kafka = new Kafka(this.config);
        console.log('🔌 KafkaClient initialized with shared config');
    }

    async initialize(): Promise<boolean> {
        try {
            await this.createTopics();
            this.isAvailable = true;
            console.log('✅ Kafka initialized successfully');
            return true;
        } catch (error) {
            console.error('❌ Kafka initialization failed:', error);
            this.isAvailable = false;
            return false;
        }
    }

    public isKafkaAvailable(): boolean {
        return this.isAvailable;
    }

    public static getInstance(): KafkaClient {
        if (!KafkaClient.instance) {
            KafkaClient.instance = new KafkaClient();
        }
        return KafkaClient.instance;
    }

    async getProducer(): Promise<Producer> {
        if (!this.isAvailable) {
            throw new Error('Kafka is not available');
        }
        if (!this.producer) {
            this.producer = this.kafka.producer();
            await this.producer.connect();
            console.log('📤 Kafka Producer connected');
        }
        return this.producer;
    }

    async getConsumer(groupId: string): Promise<Consumer> {
        if (!this.consumer) {
            this.consumer = this.kafka.consumer({ groupId });
            await this.consumer.connect();
            console.log('📥 Kafka Consumer connected');
        }
        return this.consumer;
    }

    async createTopics(): Promise<void> {
        const admin = this.kafka.admin();

        try {
            await admin.connect();

            const topics = Object.values(this.topics).map((config) => ({
                topic: config.topic,
                numPartitions: config.partitions,
                replicationFactor: config.replicationFactor,
                configEntries: Object.entries(config.config || {}).map(([key, value]) => ({
                    name: key,
                    value: String(value)
                }))
            }));

            await admin.createTopics({
                topics,
                waitForLeaders: true,
            });

            console.log('📋 Kafka topics created successfully');
        } catch (error) {
            console.error('❌ Error creating Kafka topics:', error);
            throw error;
        } finally {
            await admin.disconnect();
        }
    }

    async disconnect(): Promise<void> {
        if (this.producer) {
            await this.producer.disconnect();
            this.producer = null;
        }
        if (this.consumer) {
            await this.consumer.disconnect();
            this.consumer = null;
        }
        console.log('🔌 Kafka connections closed');
    }

    getTopicName(topicKey: keyof TopicsConfig): string {
        return this.topics[topicKey].topic;
    }
}

export default KafkaClient;