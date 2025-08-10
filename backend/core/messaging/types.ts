export interface BaseEvent {
    eventId: string;
    eventType: string;
    aggregateId: string;
    timestamp: string;
    version: string;
    data: Record<string, any>;
    metadata?: Record<string, any>;
}

export interface UserEvent extends BaseEvent {
    // aggregateId = userId
    eventType: 'USER_CREATED' | 'USER_UPDATED' | 'USER_FOLLOWED' | 'USER_UNFOLLOWED' | 'USER_LOGIN' | 'USER_LOGOUT';
}

export interface PostEvent extends BaseEvent {
    // aggregateId = postId
    eventType: 'POST_CREATED' | 'POST_UPDATED' | 'POST_DELETED';
}

export interface BehaviorEvent extends BaseEvent {
    // aggregateId could be postId, userId, commentId, etc., depending on the behavior type
    eventType: 'POST_VIEWED' | 'POST_LIKED' | 'POST_SAVED' | 'SEARCH_PERFORMED' | 'COMMENT_CREATED';
    sessionId?: string;
}
