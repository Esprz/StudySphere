import request from 'supertest';
import express from 'express';
import recommendationRouter from '../routes/recommendationRouter';
import prisma from '../utils/prisma';
import { readCacheValue } from '../utils/redis';
import { generateAccessToken } from '../utils/jwt';

jest.mock('../utils/prisma', () => ({
    __esModule: true,
    default: {
        post: {
            findMany: jest.fn(),
        },
        user: {
            findMany: jest.fn(),
        },
    },
}));

jest.mock('../utils/redis', () => ({
    __esModule: true,
    default: {},
    readCacheValue: jest.fn(),
    initRedis: jest.fn(),
}));

const app = express();
app.use(express.json());
app.use('/recommendations', recommendationRouter);

describe('Recommendation Routes', () => {
    const token = generateAccessToken('user-1');
    const originalFetch = global.fetch;

    beforeEach(() => {
        global.fetch = jest.fn();
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    afterAll(() => {
        global.fetch = originalFetch;
    });

    test('GET /recommendations/feed returns Redis-backed recommendations in cached order', async () => {
        (readCacheValue as jest.Mock).mockResolvedValue(
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
        (readCacheValue as jest.Mock).mockResolvedValue(null);
        (global.fetch as jest.Mock).mockResolvedValue({
            ok: false,
        });
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

    test('GET /recommendations/feed calls recommender on cache miss before chronological fallback', async () => {
        (readCacheValue as jest.Mock).mockResolvedValue(null);
        (global.fetch as jest.Mock).mockResolvedValue({
            ok: true,
            json: async () => ({
                posts: [
                    {
                        post_id: 'post-r1',
                        title: 'Recommended by service',
                        user: { user_id: 'author-r1', username: 'remote', avatar_url: null },
                    },
                ],
            }),
        });

        const response = await request(app)
            .get('/recommendations/feed')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).toBe(200);
        expect(response.body.source).toBe('recommender');
        expect(response.body.posts[0].post_id).toBe('post-r1');
        expect(prisma.post.findMany).not.toHaveBeenCalled();
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/recommendations/user-1?limit=20')
        );
    });

    test('GET /recommendations/users returns cached user recommendations', async () => {
        (readCacheValue as jest.Mock).mockResolvedValueOnce(
            JSON.stringify([
                {
                    user_id: 'user-2',
                    username: 'alice',
                    display_name: 'Alice',
                    bio: 'bio',
                    score: 1.0,
                    source: 'user_cf+user_embedding',
                },
            ])
        );

        const response = await request(app)
            .get('/recommendations/users')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).toBe(200);
        expect(response.body.source).toBe('recommended_users');
        expect(response.body.users).toHaveLength(1);
        expect(prisma.user.findMany).not.toHaveBeenCalled();
    });

    test('GET /recommendations/users falls back to popular users', async () => {
        (readCacheValue as jest.Mock).mockResolvedValueOnce(null);
        (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false });
        (prisma.user.findMany as jest.Mock).mockResolvedValueOnce([
            {
                user_id: 'user-3',
                username: 'bob',
                display_name: 'Bob',
                avatar_url: null,
                bio: 'bio3',
            },
        ]);

        const response = await request(app)
            .get('/recommendations/users')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).toBe(200);
        expect(response.body.source).toBe('popular_users');
        expect(response.body.users[0].user_id).toBe('user-3');
    });

    test('GET /recommendations/users calls recommender on cache miss before DB fallback', async () => {
        (readCacheValue as jest.Mock).mockResolvedValueOnce(null);
        (global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                recommendations: [
                    {
                        user_id: 'user-4',
                        username: 'remote-user',
                        display_name: 'Remote User',
                        bio: 'bio4',
                        score: 1.25,
                        source: 'user_cf+user_embedding',
                    },
                ],
            }),
        });

        const response = await request(app)
            .get('/recommendations/users')
            .set('Authorization', `Bearer ${token}`);

        expect(response.status).toBe(200);
        expect(response.body.source).toBe('recommender_users');
        expect(response.body.users[0].user_id).toBe('user-4');
        expect(prisma.user.findMany).not.toHaveBeenCalled();
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/recommendations/users/user-1?limit=5')
        );
    });
});
