import request from 'supertest';
import express from 'express';
import likeRouter from '../routes/likeRouter';
import * as likeService from '../services/likeService';
import { generateAccessToken } from '../utils/jwt';
import { LIKE_SUCCESS } from '../constants/successMessages';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS, LIKE_ERRORS } from '../constants/errorMessages';

// Mock the likeService module
jest.mock('../services/likeService', () => ({
    likePost: jest.fn(),
    deleteLike: jest.fn(),
    getLikedPosts: jest.fn(),
}));

const dummyLikes = [
    { like_id: '1', post_id: '101', user_id: 'test-user-id' },
    { like_id: '2', post_id: '102', user_id: 'test-user-id' },
];
const dummyLike = { like_id: '1', post_id: '101', user_id: 'test-user-id' };

const app = express();
app.use(express.json());
app.use('/like', likeRouter);

describe('Like Routes', () => {
    let token: string;

    beforeAll(() => {
        // Generate a valid token for testing
        token = generateAccessToken('test-user-id');
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('POST /like/:post_id should like a post', async () => {
        (likeService.likePost as jest.Mock).mockResolvedValue(dummyLike);

        const res = await request(app)
            .post('/like/101')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send({ user_id: 'test-user-id' });

        expect(res.status).toBe(HTTP.CREATED.code);
        expect(res.body).toEqual(dummyLike);
        expect(likeService.likePost).toHaveBeenCalledWith('101', 'test-user-id');
    });

    test('POST /like/:post_id should return 409 if post is already liked', async () => {
        (likeService.likePost as jest.Mock).mockResolvedValue(null);

        const res = await request(app)
            .post('/like/101')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send({ user_id: 'test-user-id' });

        expect(res.status).toBe(HTTP.CONFLICT.code);
        expect(res.body).toEqual({ message: LIKE_ERRORS.ALREADY_LIKED });
    });

    test('DELETE /like/:like_id should delete a liked post', async () => {
        (likeService.deleteLike as jest.Mock).mockResolvedValue({});

        const res = await request(app)
            .delete('/like/1')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ message: LIKE_SUCCESS.DELETED });
        expect(likeService.deleteLike).toHaveBeenCalledWith('1');
    });

    test('GET /like should return all liked posts for a user', async () => {
        (likeService.getLikedPosts as jest.Mock).mockResolvedValue(dummyLikes);

        const res = await request(app)
            .get('/like')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(200);
        expect(res.body).toEqual(dummyLikes);
        expect(likeService.getLikedPosts).toHaveBeenCalledWith('test-user-id');
    });

    test('GET /like should return 500 on server error', async () => {
        (likeService.getLikedPosts as jest.Mock).mockRejectedValue(new Error('Internal server error'));

        const res = await request(app)
            .get('/like')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(500);
        expect(res.body).toEqual({ message: GENERAL_ERRORS.UNKNOWN });
    });
});