import request from 'supertest';
import express from 'express';
import searchRouter from '../routes/searchRouter';
import * as postService from '../services/postService';
import { HTTP } from '../constants/httpStatus';
import { POST_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';

// Mock the postService module
jest.mock('../services/postService', () => ({
    searchPosts: jest.fn(),
}));

const dummyPosts = [
    { post_id: '1', title: 'Post 1', content: 'Content 1' },
    { post_id: '2', title: 'Post 2', content: 'Content 2' },
];

const app = express();
app.use(express.json());
app.use('/search', searchRouter);

describe('Search Routes', () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    test('GET /search should return posts matching the query', async () => {
        (postService.searchPosts as jest.Mock).mockResolvedValue(dummyPosts);

        const res = await request(app).get('/search').query({ q: 'Post' });

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual(dummyPosts);
        expect(postService.searchPosts).toHaveBeenCalledWith('Post');
    });

    test('GET /search should return 400 if query parameter is missing', async () => {
        const res = await request(app).get('/search');

        expect(res.status).toBe(HTTP.BAD_REQUEST.code);
        expect(res.body).toEqual({ message: POST_ERRORS.MISSING_FIELDS });
    });

    test('GET /search should return 400 if query parameter is invalid', async () => {
        const res = await request(app).get('/search').query({ q: '' }); // Invalid query type

        expect(res.status).toBe(HTTP.BAD_REQUEST.code);
        expect(res.body).toEqual({ message: POST_ERRORS.MISSING_FIELDS });
    });

    test('GET /search should return 500 if an unexpected error occurs', async () => {
        (postService.searchPosts as jest.Mock).mockRejectedValue(new Error('Internal server error'));

        const res = await request(app).get('/search').query({ q: 'Post' });

        expect(res.status).toBe(HTTP.INTERNAL_ERROR.code);
        expect(res.body).toEqual({ message: GENERAL_ERRORS.UNKNOWN });
    });
});