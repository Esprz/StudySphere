import { BaseProducer } from './BaseProducer';
import { BehaviorEvent } from '../../core/messaging/types';
import { topicConfigs } from '../../config/kafka';

export class BehaviorEventProducer extends BaseProducer<BehaviorEvent> {
    protected topic: string = topicConfigs.BEHAVIOR_EVENTS.topic;

    async trackPostViewed(
        postId: string,
        userId: string,
        sessionId?: string,
        dwellMs?: number,
        position?: number
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'POST_VIEWED',
            postId,  // aggregateId = postId
            {
                userId,
                viewedAt: new Date(),
                dwellMs: dwellMs ?? null,
                position: position ?? null
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

    async trackPostSaved(postId: string, userId: string, sessionId?: string): Promise<void> {
        const baseEvent = this.createEvent(
            'POST_SAVED',
            postId,  // aggregateId = postId
            {
                userId,
                savedAt: new Date()
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'POST_SAVED',
            sessionId
        };

        await this.publish(behaviorEvent);
        console.log(`💾 User ${userId} saved post ${postId}`);
    }

    async trackSearchPerformed(
        userId: string,
        query: string,
        resultCount: number,
        sessionId?: string
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'SEARCH_PERFORMED',
            userId,  // aggregateId = userId
            {
                query,
                searchedAt: new Date(),
                resultCount
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

    async trackCommentCreated(
        commentId: string,
        userId: string,
        postId: string,
        parentId?: string,
        sessionId?: string
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'COMMENT_CREATED',
            commentId,
            {
                userId,
                postId,
                parentId: parentId ?? null,
                createdAt: new Date(),
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'COMMENT_CREATED',
            sessionId,
        };

        await this.publish(behaviorEvent);
        console.log(`💬 User ${userId} commented on post ${postId}`);
    }

    async trackFocusStarted(
        focusTimeId: string,
        userId: string,
        goalId?: string,
        tags?: string[],
        sourceTrigger?: string,
        sessionId?: string
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'START_FOCUS',
            focusTimeId,
            {
                userId,
                goalId: goalId ?? null,
                tags: tags ?? [],
                sourceTrigger: sourceTrigger ?? null,
                startedAt: new Date(),
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'START_FOCUS',
            sessionId,
        };

        await this.publish(behaviorEvent);
    }

    async trackFocusEnded(
        focusTimeId: string,
        userId: string,
        goalId?: string,
        durationMs?: number,
        sessionId?: string
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'END_FOCUS',
            focusTimeId,
            {
                userId,
                goalId: goalId ?? null,
                durationMs: durationMs ?? null,
                endedAt: new Date(),
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'END_FOCUS',
            sessionId,
        };

        await this.publish(behaviorEvent);
    }

    async trackTaskAdded(
        taskId: string,
        userId: string,
        content: string,
        goalId?: string,
        sessionId?: string
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'ADD_TASK',
            taskId,
            {
                userId,
                goalId: goalId ?? null,
                content,
                createdAt: new Date(),
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'ADD_TASK',
            sessionId,
        };

        await this.publish(behaviorEvent);
    }

    async trackTaskCompleted(
        taskId: string,
        userId: string,
        goalId?: string,
        sessionId?: string
    ): Promise<void> {
        const baseEvent = this.createEvent(
            'COMPLETE_TASK',
            taskId,
            {
                userId,
                goalId: goalId ?? null,
                completedAt: new Date(),
            },
            { sessionId }
        );

        const behaviorEvent: BehaviorEvent = {
            ...baseEvent,
            eventType: 'COMPLETE_TASK',
            sessionId,
        };

        await this.publish(behaviorEvent);
    }
}
