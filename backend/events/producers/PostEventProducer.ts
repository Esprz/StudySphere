import { BaseProducer } from "./BaseProducer";
import { PostEvent } from "../../core/messaging/types";
import { topicConfigs } from "../../config/kafka";

export class PostEventProducer extends BaseProducer<PostEvent> {
  protected topic: string = topicConfigs.POST_EVENTS.topic;

  async trackPostCreated(
    postId: string,
    userId: string,
    postData: any
  ): Promise<void> {
    const baseEvent = this.createEvent(
      "POST_CREATED",
      postId, // aggregateId = postId
      {
        authorId: userId,
        title: postData.title,
        content: postData.content,
        tags: postData.tags,
        createdAt: new Date(),
      }
    );

    const postEvent: PostEvent = {
      ...baseEvent,
      eventType: "POST_CREATED",
    };

    await this.publish(postEvent);
    console.log(`📝 Post ${postId} created by user ${userId}`);
  }

  async trackPostUpdated(
    postId: string,
    userId: string,
    updateData: any
  ): Promise<void> {
    const baseEvent = this.createEvent(
      "POST_UPDATED",
      postId, // aggregateId = postId
      {
        authorId: userId,
        updatedFields: updateData,
        updatedAt: new Date(),
      }
    );

    const postEvent: PostEvent = {
      ...baseEvent,
      eventType: "POST_UPDATED",
    };

    await this.publish(postEvent);
    console.log(`✏️ Post ${postId} updated by user ${userId}`);
  }

  async trackPostDeleted(postId: string, userId: string): Promise<void> {
    const baseEvent = this.createEvent(
      "POST_DELETED",
      postId, // aggregateId = postId
      {
        authorId: userId,
        deletedAt: new Date(),
      }
    );

    const postEvent: PostEvent = {
      ...baseEvent,
      eventType: "POST_DELETED",
    };

    await this.publish(postEvent);
    console.log(`🗑️ Post ${postId} deleted by user ${userId}`);
  }
}
