import KafkaClient from './KafkaClient';
import { BaseEvent } from './types';

class EventBus {
    private static instance: EventBus;
    private kafkaClient: KafkaClient;

    private constructor() {
        this.kafkaClient = KafkaClient.getInstance();
    }

    static getInstance(): EventBus {
        if (!EventBus.instance) {
            EventBus.instance = new EventBus();
        }
        return EventBus.instance;
    }

    async publish<T extends BaseEvent>(topic: string, event: T): Promise<void> {

        if (!this.kafkaClient.isKafkaAvailable()) {
            console.log(`📤 Event skipped (Kafka unavailable): ${event.eventType} to ${topic}`);
            return;
        }

        try {
            const producer = await this.kafkaClient.getProducer();
            await producer.send({
                topic,
                messages: [{
                    key: event.aggregateId || event.eventId,
                    value: JSON.stringify(event),
                    timestamp: Date.now().toString(),
                    headers: {
                        eventType: event.eventType,
                        version: event.version || '1.0',
                        source: 'studysphere-backend',
                    }
                }]
            });
            console.log(`📤 Event published: ${event.eventType} to ${topic}`);
        } catch (error) {
            console.error(`❌ Failed to publish event: ${event.eventType}`, error);
            // Could add retry logic or store in a dead letter queue
            throw error;
        }
    }

    async subscribe<T extends BaseEvent>(
        topic: string,
        groupId: string,
        handler: (event?: T) => Promise<void>
    ): Promise<void> {
        if (!this.kafkaClient.isKafkaAvailable()) {
            console.log(`📥 Subscription skipped (Kafka unavailable): ${topic} with group ${groupId}`);
            return;
        }

        try {
            const consumer = await this.kafkaClient.getConsumer(groupId);
            await consumer.subscribe({ topic });

            await consumer.run({
                eachMessage: async ({ message }) => {
                    try {
                        const event = JSON.parse(message.value?.toString() || '{}');
                        await handler(event);
                        console.log(`📥 Event processed: ${event.eventType} from ${topic}`);
                    } catch (error) {
                        console.error(`❌ Error processing message from ${topic}:`, error);
                    }
                }
            });
            console.log(`📥 Subscribed to topic ${topic} with group ${groupId}`);
        } catch (error) {
            console.error(`❌ Failed to subscribe to ${topic}:`, error);
            throw error;
        }
    }
}

export default EventBus;