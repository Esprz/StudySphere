import EventBus from '../../core/messaging/EventBus';
import { BaseEvent } from '../../core/messaging/types';
import { v4 as uuidv4 } from 'uuid';

export abstract class BaseProducer<T extends BaseEvent> {
    protected eventBus: EventBus;
    protected abstract topic: string;

    constructor() {
        this.eventBus = EventBus.getInstance();
    }

    protected createEvent(
        eventType: string,
        aggregateId: string,
        data: Record<string, any>,
        metadata?: Record<string, any>
    ): BaseEvent {
        return {
            eventId: uuidv4(),
            eventType,
            aggregateId,
            timestamp: new Date().toISOString(),
            version: '1.0',
            data,
            metadata: {
                ...metadata,
                source: 'studysphere-backend',
                environment: process.env.NODE_ENV || 'development',
            }
        };
    }

    async publish(event: T): Promise<void> {
        await this.eventBus.publish(this.topic, event);
    }
}