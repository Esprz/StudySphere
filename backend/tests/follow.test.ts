import request from 'supertest';
import express from 'express';
import followRouter from '../routes/followRouter';
import * as followService from '../services/followService';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS, FOLLOW_ERRORS } from '../constants/errorMessages';
import { generateAccessToken } from '../utils/jwt';

// Mock the followService module
jest.mock('../services/followService', () => ({
    createFollow: jest.fn(),
    deleteFollow: jest.fn(),
    getFollowers: jest.fn(),
    getFollowees: jest.fn(),
}));

const dummyFollowers = [
    { follow_id: '1', follower_id: 'user1', followee_id: 'user2' },
    { follow_id: '2', follower_id: 'user3', followee_id: 'user2' },
];
const dummyFollowees = [
    { follow_id: '1', follower_id: 'user2', followee_id: 'user1' },
    { follow_id: '2', follower_id: 'user2', followee_id: 'user3' },
];
const dummyFollow = { follow_id: '1', follower_id: 'user2', followee_id: 'user1' };

const app = express();
app.use(express.json());
app.use('/follow', followRouter);

describe('Follow Routes', () => {
    let token: string;

    beforeAll(() => {
        // Generate a valid token for testing
        token = generateAccessToken('user2');
    });
    afterEach(() => {
        jest.clearAllMocks();
    });

    test('POST /:followee_id should create a follow relationship', async () => {
        (followService.createFollow as jest.Mock).mockResolvedValue(dummyFollow);

        const res = await request(app)
            .post('/follow/user1')
            .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(HTTP.CREATED.code);
        expect(res.body).toEqual(dummyFollow);
        expect(followService.createFollow).toHaveBeenCalledWith('user1', 'user2');
    });

    test('POST /:followee_id should return 409 if already followed', async () => {
        (followService.createFollow as jest.Mock).mockResolvedValue(null);

        const res = await request(app)
            .post('/follow/user2')
            .set('Authorization', `Bearer ${token}`)
            .send({ user_id: 'user1' });

        expect(res.status).toBe(HTTP.CONFLICT.code);
        expect(res.body).toEqual({ message: FOLLOW_ERRORS.ALREADY_FOLLOWED });
    });

    test('DELETE /follow/:follow_id should delete a follow relationship', async () => {
        (followService.deleteFollow as jest.Mock).mockResolvedValue({});

        const res = await request(app)
            .delete('/follow/1')            
            .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual({ message: 'Follow deleted.' });
        expect(followService.deleteFollow).toHaveBeenCalledWith('1');
    });

    test('GET /followers should return all followers for current user', async () => {
        (followService.getFollowers as jest.Mock).mockResolvedValue(dummyFollowers);

        const res = await request(app)
            .get('/follow/followers')            
            .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual(dummyFollowers);
        expect(followService.getFollowers).toHaveBeenCalledWith('user2');
    });

    test('GET /followees should return all followees for current user', async () => {
        (followService.getFollowees as jest.Mock).mockResolvedValue(dummyFollowees);

        const res = await request(app)
            .get('/follow/followees')            
            .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual(dummyFollowees);
        expect(followService.getFollowees).toHaveBeenCalledWith('user2');
    });

    test('GET /followers should return 500 if an unexpected error occurs', async () => {
        (followService.getFollowers as jest.Mock).mockRejectedValue(new Error('Internal server error'));

        const res = await request(app)
            .get('/follow/followers')            
            .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(HTTP.INTERNAL_ERROR.code);
        expect(res.body).toEqual({ message: GENERAL_ERRORS.UNKNOWN });
    });
});