import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import prisma from './utils/prisma';
import router from './routes';

// Configure dotenv
dotenv.config();

const app = express();
const PORT = process.env.PORT;


// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api', router);

// Example route to test the server
app.get('/', (req: Request, res: any) => {
    res.send('Server is running!');
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});

// Disconnet prisma
process.on('SIGINT', async () => {
    await prisma.$disconnect();
    process.exit(0);
});
process.on('SIGTERM', async () => {
    await prisma.$disconnect();
    process.exit(0);
});