import request from 'supertest';
import express from 'express';
import saveRouter from '../routes/saveRouter';
import * as saveService from '../services/saveService';
import { generateAccessToken } from '../utils/jwt';

// Mock the saveService module
jest.mock('../services/saveService', () => ({
    savePost: jest.fn(),
    deleteSave: jest.fn(),
    getSavedPosts: jest.fn(),
}));

const dummySaves = [
    { save_id: '1', post_id: '101', user_id: 'test-user-id' },
    { save_id: '2', post_id: '102', user_id: 'test-user-id' },
];
const dummySave = { save_id: '1', post_id: '101', user_id: 'test-user-id' };

const app = express();
app.use(express.json());
app.use('/save', saveRouter);

describe('Save Routes', () => {
    let token: string;

    beforeAll(() => {
        // Generate a valid token for testing
        token = generateAccessToken('test-user-id');
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('POST /save/:post_id should save a post', async () => {
        (saveService.savePost as jest.Mock).mockResolvedValue(dummySave);

        const res = await request(app)
            .post('/save/101')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send({ user_id: 'test-user-id' });

        expect(res.status).toBe(201);
        expect(res.body).toEqual(dummySave);
        expect(saveService.savePost).toHaveBeenCalledWith('101', 'test-user-id');
    });

    test('POST /save/:post_id should return 409 if post is already saved', async () => {
        (saveService.savePost as jest.Mock).mockResolvedValue(null);

        const res = await request(app)
            .post('/save/101')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send({ user_id: 'test-user-id' });

        expect(res.status).toBe(409);
        expect(res.body).toEqual({ message: 'Post already saved.' });
    });

    test('DELETE /save/:save_id should delete a saved post', async () => {
        (saveService.deleteSave as jest.Mock).mockResolvedValue({});

        const res = await request(app)
            .delete('/save/1')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(200);
        expect(res.body).toEqual({ message: 'Save deleted successfully.' });
        expect(saveService.deleteSave).toHaveBeenCalledWith('1');
    });

    test('GET /save/:user_id should return all saved posts for a user', async () => {
        (saveService.getSavedPosts as jest.Mock).mockResolvedValue(dummySaves);

        const res = await request(app)
            .get('/save')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(200);
        expect(res.body).toEqual(dummySaves);
        expect(saveService.getSavedPosts).toHaveBeenCalledWith('test-user-id');
    });

    test('GET /save/:user_id should return 500 on server error', async () => {
        (saveService.getSavedPosts as jest.Mock).mockRejectedValue(new Error('Internal server error'));

        const res = await request(app)
            .get('/save')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(500);
        expect(res.body).toEqual({ message: 'An unexpected error occurred.' });
    });
});