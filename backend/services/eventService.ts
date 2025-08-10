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
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackPostViewed(postId, userId, sessionId);
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
    sessionId?: string
  ): Promise<void> {
    await this.behaviorProducer.trackSearchPerformed(userId, query, sessionId);
  }

  async trackUserCreated(userId: string, userData: any): Promise<void> {
    await this.userProducer.trackUserCreated(userId, userData);
  }

}

export const eventService = new EventService();
