import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import postsRouter from './routes/postRouter';
import authRouter from './routes/authRouter';

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



// Example route to test the server
app.get('/', (req: Request, res: any) => {
    res.send('Server is running!');
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});