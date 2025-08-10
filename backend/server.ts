import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import cookieParser from 'cookie-parser';
import prisma from './utils/prisma';
import router from './routes';
import KafkaClient from './core/messaging/KafkaClient';

// Configure dotenv
dotenv.config();

const app = express();
const PORT = process.env.PORT;


// Middleware
app.use(cors({
    origin: 'http://localhost:5173',
    credentials: true, 
}));
app.use(cookieParser());
app.use(express.json());

// Routes
app.use('/api', router);

// Example route to test the server
app.get('/', (req: Request, res: any) => {
    res.send('Server is running!');
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
});

// Graceful shutdown
const gracefulShutdown = async () => {
    console.log('Shutting down gracefully...');
    try {
        const kafkaClient = KafkaClient.getInstance();
        await kafkaClient.disconnect();
        await prisma.$disconnect();
    } catch (error) {
        console.error('Error during shutdown:', error);
    }
    process.exit(0);
};

process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);