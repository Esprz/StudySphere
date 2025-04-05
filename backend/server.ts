import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import prisma from './utils/prisma';
import postsRouter from './routes/postRouter';
import authRouter from './routes/authRouter';
import saveRouter from './routes/saveRouter';
import likeRouter from './routes/likeRouter'
import searchRouter from './routes/searchRouter'

// Configure dotenv
dotenv.config();

const app = express();
const PORT = process.env.PORT;


// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/posts', postsRouter);
app.use('/auth', authRouter);
app.use('/save', saveRouter);
app.use('/like', likeRouter);
app.use('/search', searchRouter);

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