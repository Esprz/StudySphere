import request from 'supertest';
import express from 'express';
import recommendationRouter from '../routes/recommendationRouter';
import prisma from '../utils/prisma';
import redis, { isRedisConnected } from '../utils/redis';
import { generateAccessToken } from '../utils/jwt';

jest.mock('../utils/prisma', () => ({
    __esModule: true,
    default: {
        post: {
            findMany: jest.fn(),
        },
    },
}));

jest.mock('../utils/redis', () => ({
    __esModule: true,
    default: {
        get: jest.fn(),
        ping: jest.fn(),
        quit: jest.fn(),
    },
    isRedisConnected: jest.fn(),
    initRedis: jest.fn(),
}));

const app = express();
app.use(express.json());
app.use('/recommendations', recommendationRouter);

describe('Recommendation Routes', () => {
    const token = generateAccessToken('user-1');

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('GET /recommendations/feed returns Redis-backed recommendations in cached order', async () => {
        (isRedisConnected as jest.Mock).mockReturnValue(true);
        (redis.get as jest.Mock).mockResolvedValue(
            JSON.stringify([
                { post_id: 'post-2', score: 0.9, source: 'content_based' },
                { post_id: 'post-1', score: 0.7, source: 'content_based' },
            ]),
        );
        (prisma.post.findMany as jest.Mock).mockResolvedValue([
            {
                post_id: 'post-1',
                title: 'Post 1',
                user: { user_id: 'author-1', username: 'alice', avatar_url: null },
            },
            {
                post_id: 'post-2',
                title: 'Post 2',
                user: { user_id: 'author-2', username: 'bob', avatar_url: null },
            },
        ]);

        const response = await request(app)
            .get('/recommendations/feed')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).toBe(200);
        expect(response.body.source).toBe('recommended');
        expect(response.body.posts.map((post: { post_id: string }) => post.post_id)).toEqual([
            'post-2',
            'post-1',
        ]);
    });

    test('GET /recommendations/feed falls back to chronological posts when Redis is unavailable', async () => {
        (isRedisConnected as jest.Mock).mockReturnValue(false);
        (prisma.post.findMany as jest.Mock).mockResolvedValue([
            {
                post_id: 'post-3',
                title: 'Newest Post',
                user: { user_id: 'author-3', username: 'cara', avatar_url: null },
            },
        ]);

        const response = await request(app)
            .get('/recommendations/feed')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).toBe(200);
        expect(response.body.source).toBe('chronological');
        expect(response.body.posts).toHaveLength(1);
        expect(prisma.post.findMany).toHaveBeenCalledWith(
            expect.objectContaining({
                take: 20,
                orderBy: { created_at: 'desc' },
            }),
        );
    });
});
