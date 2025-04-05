import request from 'supertest';
import express from 'express';
import postRouter from '../routes/postRouter';
import * as postService from '../services/postService';
import { generateAccessToken } from '../utils/jwt';

// Mock the postService module
jest.mock('../services/postService', () => ({
    getAllPosts: jest.fn(),
    getRecentPosts: jest.fn(),
    getPostById: jest.fn(),
    createPost: jest.fn(),
    updatePost: jest.fn(),
    deletePost: jest.fn(),
    getPaginatedPosts: jest.fn(),
}));

const dummyPosts = [{ post_id: '1', title: 'Post 1' }, { post_id: '2', title: 'Post 2' }];
const dummyPost = { post_id: '1', title: 'Post 1' };

const app = express();
app.use(express.json());
app.use('/post', postRouter);

describe('Post Routes', () => {
    let token: string;

    beforeAll(() => {
        // Generate a valid token for testing
        token = generateAccessToken('test-user-id');
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('GET /post should return all posts', async () => {
        (postService.getAllPosts as jest.Mock).mockResolvedValue(dummyPosts);

        const res = await request(app).get('/post');
        expect(res.status).toBe(200);
        expect(res.body).toEqual(dummyPosts);
        expect(postService.getAllPosts).toHaveBeenCalledTimes(1);
    });

    test('GET /post/recent should return recent posts', async () => {
        (postService.getRecentPosts as jest.Mock).mockResolvedValue(dummyPosts);

        const res = await request(app).get('/post/recent');
        expect(res.status).toBe(200);
        expect(res.body).toEqual(dummyPosts);
        expect(postService.getRecentPosts).toHaveBeenCalledTimes(1);
    });

    test('GET /post/:post_id should return a post if found', async () => {
        (postService.getPostById as jest.Mock).mockResolvedValue(dummyPost);

        const res = await request(app).get('/post/1');
        expect(res.status).toBe(200);
        expect(res.body).toEqual(dummyPost);
        expect(postService.getPostById).toHaveBeenCalledWith('1');
    });

    test('GET /post/:post_id should return 404 if post not found', async () => {
        (postService.getPostById as jest.Mock).mockResolvedValue(null);

        const res = await request(app).get('/post/nonexistent');
        expect(res.status).toBe(404);
    });

    test('POST /post should create a new post', async () => {
        const newPost = { title: 'New Post', content: 'New content', user_id: 'test-user-id' };
        const createdPost = { ...newPost, post_id: '3' };
        (postService.createPost as jest.Mock).mockResolvedValue(createdPost);

        const res = await request(app)
            .post('/post')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send(newPost);

        expect(res.status).toBe(201);
        expect(res.body).toEqual(createdPost);
        expect(postService.createPost).toHaveBeenCalledWith(newPost);
    });

    test('POST /post should return 400 when missing required fields', async () => {
        const incompletePost = { title: 'Incomplete Post', content: 'Missing user_id' };
        const res = await request(app)
            .post('/post')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send(incompletePost);

        expect(res.status).toBe(400);
    });

    test('PATCH /post/:post_id should update a post', async () => {
        const updates = { title: 'Updated Title' };
        const updatedPost = { post_id: '1', title: 'Updated Title' };
        (postService.updatePost as jest.Mock).mockResolvedValue(updatedPost);

        const res = await request(app)
            .patch('/post/1')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send(updates);

        expect(res.status).toBe(200);
        expect(res.body).toEqual(updatedPost);
        expect(postService.updatePost).toHaveBeenCalledWith('1', updates);
    });

    test('DELETE /post/:post_id should delete a post', async () => {
        (postService.deletePost as jest.Mock).mockResolvedValue({});

        const res = await request(app)
            .delete('/post/1')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ message: 'Post deleted successfully.' });
        expect(postService.deletePost).toHaveBeenCalledWith('1');
    });

    test('POST /post/infinite should return paginated posts', async () => {
        (postService.getPaginatedPosts as jest.Mock).mockResolvedValue(dummyPosts);

        const res = await request(app)
            .post('/post/infinite')
            .send({ page: 0 });

        expect(res.status).toBe(200);
        expect(res.body).toEqual(dummyPosts);
        expect(postService.getPaginatedPosts).toHaveBeenCalledWith(0);
    });
});