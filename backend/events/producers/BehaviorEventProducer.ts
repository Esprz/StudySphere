import { BaseProducer } from './BaseProducer';
import { BehaviorEvent } from '../../core/messaging/types';
import { topicConfigs } from '../../config/kafka';

export class BehaviorEventProducer extends BaseProducer<BehaviorEvent> {
    protected topic: string = topicConfigs.BEHAVIOR_EVENTS.topic;

    async trackPostViewed(postId: string, userId: string, sessionId?: string): Promise<void> {
        const baseEvent = this.createEvent(
            'POST_VIEWED',
            postId,  // aggregateId = postId
            {
                userId,
                viewedAt: new Date(),
                duration: null  // TODO: add viewing duration in the future
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'POST_VIEWED',
            sessionId
        };

        await this.publish(behaviorEvent);
        console.log(`📊 User ${userId} viewed post ${postId}`);
    }

    async trackPostLiked(postId: string, userId: string, sessionId?: string): Promise<void> {
        const baseEvent = this.createEvent(
            'POST_LIKED',
            postId,  // aggregateId = postId
            {
                userId,
                likedAt: new Date()
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'POST_LIKED',
            sessionId
        };

        await this.publish(behaviorEvent);
        console.log(`👍 User ${userId} liked post ${postId}`);
    }

    async trackSearchPerformed(userId: string, query: string, sessionId?: string): Promise<void> {
        const baseEvent = this.createEvent(
            'SEARCH_PERFORMED',
            userId,  // aggregateId = userId
            {
                query,
                searchedAt: new Date(),
                resultCount: 0 // TODO: add result count
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'SEARCH_PERFORMED',
            sessionId
        };

        await this.publish(behaviorEvent);
        console.log(`🔍 User ${userId} searched for "${query}"`);
    }
}