import { BaseProducer } from "./BaseProducer";
import { UserEvent } from "../../core/messaging/types";
import { topicConfigs } from "../../config/kafka";

export class UserEventProducer extends BaseProducer<UserEvent> {
  protected topic: string = topicConfigs.USER_EVENTS.topic;

  async trackUserCreated(
    userId: string,
    userData: any
  ): Promise<void> {
    const baseEvent = this.createEvent(
      "USER_CREATED",
      userId, // aggregateId = userId
      {
        ...userData,
        createdAt: new Date(),
      }
    );

    const userEvent: UserEvent = {
      ...baseEvent,
      eventType: "USER_CREATED",
    };

    await this.publish(userEvent);
    console.log(`👤 User ${userId} created`);
  }

  async trackUserFollowed(
    followerId: string,
    followeeId: string
  ): Promise<void> {
    const baseEvent = this.createEvent(
      "USER_FOLLOWED",
      followerId,
      {
        followeeId,
        followedAt: new Date(),
      }
    );

    const userEvent: UserEvent = {
      ...baseEvent,
      eventType: "USER_FOLLOWED",
    };

    await this.publish(userEvent);
  }

  async trackUserUnfollowed(
    followerId: string,
    followeeId: string
  ): Promise<void> {
    const baseEvent = this.createEvent(
      "USER_UNFOLLOWED",
      followerId,
      {
        followeeId,
        unfollowedAt: new Date(),
      }
    );

    const userEvent: UserEvent = {
      ...baseEvent,
      eventType: "USER_UNFOLLOWED",
    };

    await this.publish(userEvent);
  }

}
