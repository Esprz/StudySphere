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


}
