import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import cookieParser from 'cookie-parser';
import prisma from './utils/prisma';
import router from './routes';
import KafkaClient from './core/messaging/KafkaClient';
import redis, { initRedis, isRedisConnected } from './utils/redis';

dotenv.config();

const app = express();
const PORT = process.env.PORT;

app.use(cors({
    origin: 'http://localhost:5173',
    credentials: true, 
}));
app.use(cookieParser());
app.use(express.json());

app.use('/api', router);

app.get('/', (_req, res) => {
    res.send('Server is running!');
});

app.get('/api/health', async (_req, res) => {
    const dependencies: Record<string, string> = {
        postgres: 'error',
        redis_cache: 'error',
        redis_session: 'error',
        kafka: 'error',
    };

    try {
        await prisma.$queryRaw`SELECT 1`;
        dependencies.postgres = 'ok';
    } catch {
        dependencies.postgres = 'error';
    }

    try {
        const redisHealthy = isRedisConnected() && (await redis.ping()) === 'PONG';
        dependencies.redis_cache = redisHealthy ? 'ok' : 'error';
        dependencies.redis_session = redisHealthy ? 'ok' : 'error';
    } catch {
        dependencies.redis_cache = 'error';
        dependencies.redis_session = 'error';
    }

    try {
        const kafkaClient = KafkaClient.getInstance();
        dependencies.kafka = kafkaClient.isKafkaAvailable() ? 'ok' : 'error';
    } catch {
        dependencies.kafka = 'error';
    }

    let status: 'ok' | 'degraded' | 'error' = 'ok';
    if (dependencies.postgres === 'error') {
        status = 'error';
    } else if (Object.values(dependencies).some((value) => value === 'error')) {
        status = 'degraded';
    }

    const httpStatus = status === 'ok' ? 200 : status === 'degraded' ? 200 : 503;
    res.status(httpStatus).json({ status, dependencies });
});

// Initialize Kafka
async function initializeKafka() {
    try {
        const kafkaClient = KafkaClient.getInstance();
        const isInitialized = await kafkaClient.initialize();
        
        if (isInitialized) {
            console.log('✅ Kafka initialized successfully');
        } else {
            console.log('⚠️  Kafka not available, continuing in standalone mode...');
        }
    } catch (error) {
        console.error('❌ Kafka initialization failed:', error);
        console.log('📋 Continuing without Kafka...');
    }
}

// Start the server
app.listen(PORT, async () => {
    console.log(`🚀 StudySphere Backend running at http://localhost:${PORT}`);
    await initializeKafka();
    await initRedis();
});

// Graceful shutdown
const gracefulShutdown = async () => {
    console.log('Shutting down gracefully...');
    try {
        const kafkaClient = KafkaClient.getInstance();
        await kafkaClient.disconnect();
        await redis.quit();
        await prisma.$disconnect();
    } catch (error) {
        console.error('Error during shutdown:', error);
    }
    process.exit(0);
};

process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);
