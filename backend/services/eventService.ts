import { BehaviorEventProducer } from "../events/producers/BehaviorEventProducer";
import { PostEventProducer } from "../events/producers/PostEventProducer";
import { UserEventProducer } from '../events/producers/UserEventProducer';

class EventService {
  private behaviorProducer: BehaviorEventProducer;
  private postProducer: PostEventProducer;
  private userProducer: UserEventProducer;

  constructor() {
    this.behaviorProducer = new BehaviorEventProducer();
    this.postProducer = new PostEventProducer();
    this.userProducer = new UserEventProducer();
  }

  async trackPostCreated(
    postId: string,
    userId: string,
    postData: any
  ): Promise<void> {
    await this.postProducer.trackPostCreated(postId, userId, postData);
  }

  async trackPostUpdated(
    postId: string,
    userId: string,
    updateData: any
  ): Promise<void> {
    await this.postProducer.trackPostUpdated(postId, userId, updateData);
  }

  async trackPostDeleted(postId: string, userId: string): Promise<void> {
    await this.postProducer.trackPostDeleted(postId, userId);
  }

  async trackPostViewed(
    postId: string,
    userId: string,
    sessionId?: string,
    dwellMs?: number,
    position?: number
  ): Promise<void> {
    await this.behaviorProducer.trackPostViewed(
      postId,
      userId,
      sessionId,
      dwellMs,
      position
    );
  }

  async trackPostLiked(
    postId: string,
    userId: string,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackPostLiked(postId, userId, sessionId);
  }

  async trackPostSaved(
    postId: string,
    userId: string,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackPostSaved(postId, userId, sessionId);
  }

  async trackSearchPerformed(
    userId: string,
    query: string,
    resultCount: number,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackSearchPerformed(
      userId,
      query,
      resultCount,
      sessionId
    );
  }

  async trackCommentCreated(
    commentId: string,
    userId: string,
    postId: string,
    parentId?: string,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackCommentCreated(
      commentId,
      userId,
      postId,
      parentId,
      sessionId
    );
  }

  async trackUserCreated(userId: string, userData: any): Promise<void> {
    await this.userProducer.trackUserCreated(userId, userData);
  }

  async trackUserFollowed(followerId: string, followeeId: string): Promise<void> {
    await this.userProducer.trackUserFollowed(followerId, followeeId);
  }

  async trackUserUnfollowed(followerId: string, followeeId: string): Promise<void> {
    await this.userProducer.trackUserUnfollowed(followerId, followeeId);
  }

  async trackFocusStarted(
    focusTimeId: string,
    userId: string,
    goalId?: string,
    tags?: string[],
    sourceTrigger?: string,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackFocusStarted(
      focusTimeId,
      userId,
      goalId,
      tags,
      sourceTrigger,
      sessionId
    );
  }

  async trackFocusEnded(
    focusTimeId: string,
    userId: string,
    goalId?: string,
    durationMs?: number,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackFocusEnded(
      focusTimeId,
      userId,
      goalId,
      durationMs,
      sessionId
    );
  }

  async trackTaskAdded(
    taskId: string,
    userId: string,
    content: string,
    goalId?: string,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackTaskAdded(
      taskId,
      userId,
      content,
      goalId,
      sessionId
    );
  }

  async trackTaskCompleted(
    taskId: string,
    userId: string,
    goalId?: string,
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackTaskCompleted(
      taskId,
      userId,
      goalId,
      sessionId
    );
  }

}

export const eventService = new EventService();
