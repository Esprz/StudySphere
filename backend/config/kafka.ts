import path from "path";
import fs from "fs";
import dotenv from "dotenv";
import { KafkaConfig, TopicsConfig } from "./kafka_config_type";

const kafkaEnvPath = path.resolve(
  __dirname,
  "../../../kafka_config/.env.kafka"
);
if (fs.existsSync(kafkaEnvPath)) {
  dotenv.config({ path: kafkaEnvPath });
}

const kafkaConfigPath = path.resolve(
  __dirname,
  "../../../kafka_config/kafka.config.js"
);
const topicsConfigPath = path.resolve(
  __dirname,
  "../../../kafka_config/topics.config.js"
);

let kafkaConfig: KafkaConfig;
let topicConfigs: TopicsConfig;

if (fs.existsSync(kafkaConfigPath)) {
  kafkaConfig = require(kafkaConfigPath);
  console.log("✅ Using shared kafka config from root directory");
} else {
  // fallback configuration
  kafkaConfig = {
    brokers: [process.env.KAFKA_BROKERS || "kafka:9092"],
    clientId: "studysphere-backend",
  };
  console.log("⚠️  Using fallback kafka config");
}

if (fs.existsSync(topicsConfigPath)) {
  topicConfigs = require(topicsConfigPath);
  console.log("✅ Using shared topics config from root directory");
} else {
  // fallback configuration
  topicConfigs = {
    USER_EVENTS: {
      topic: "user-events",
      partitions: 2,
      replicationFactor: 1,
    },
    POST_EVENTS: {
      topic: "post-events",
      partitions: 3,
      replicationFactor: 1,
    },
    BEHAVIOR_EVENTS: {
      topic: "behavior-events",
      partitions: 3,
      replicationFactor: 1,
    },
  };
  console.log("⚠️  Using fallback topics config");
}

export { kafkaConfig, topicConfigs };
