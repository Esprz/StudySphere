import request from 'supertest';
import express from 'express';
import commentRouter from '../routes/commentRouter';
import * as commentService from '../services/commentService';
import { generateAccessToken } from '../utils/jwt';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';
import { COMMENT_SUCCESS } from '../constants/successMessages';

// Mock the commentService module
jest.mock('../services/commentService', () => ({
    createComment: jest.fn(),
    deleteComment: jest.fn(),
    getCommentsByPost: jest.fn(),
}));

const dummyComments = [
    { comment_id: '1', post_id: '101', user_id: 'test-user-id', content: 'First comment' },
    { comment_id: '2', post_id: '101', user_id: 'test-user-id', content: 'Second comment' },
];
const dummyComment = { comment_id: '1', post_id: '101', user_id: 'test-user-id', content: 'First comment' };

const app = express();
app.use(express.json());
app.use('/comment', commentRouter);

describe('Comment Routes', () => {
    let token: string;

    beforeAll(() => {
        // Generate a valid token for testing
        token = generateAccessToken('test-user-id');
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('POST /comment/:post_id should create a comment', async () => {
        (commentService.createComment as jest.Mock).mockResolvedValue(dummyComment);

        const res = await request(app)
            .post('/comment/101')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send({ user_id: 'test-user-id', content: 'First comment' });

        expect(res.status).toBe(HTTP.CREATED.code);
        expect(res.body).toEqual(dummyComment);
        expect(commentService.createComment).toHaveBeenCalledWith('101', 'test-user-id', 'First comment', undefined);
    });

    test('POST /comment/:post_id should return 400 if required fields are missing', async () => {
        const res = await request(app)
            .post('/comment/101')
            .set('Authorization', `Bearer ${token}`) // Provide Authorization header
            .send({ user_id: 'test-user-id' }); // Missing "content"

        expect(res.status).toBe(HTTP.BAD_REQUEST.code);
        expect(res.body).toEqual({ message: GENERAL_ERRORS.MISSING_FIELDS });
    });

    test('DELETE /comment/:comment_id should delete a comment', async () => {
        (commentService.deleteComment as jest.Mock).mockResolvedValue({});

        const res = await request(app)
            .delete('/comment/1')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual({ message: COMMENT_SUCCESS.DELETED });
        expect(commentService.deleteComment).toHaveBeenCalledWith('1');
    });

    test('GET /comment/:post_id should return all comments for a post', async () => {
        (commentService.getCommentsByPost as jest.Mock).mockResolvedValue(dummyComments);

        const res = await request(app)
            .get('/comment/101')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual(dummyComments);
        expect(commentService.getCommentsByPost).toHaveBeenCalledWith('101');
    });

    test('GET /comment/:post_id should return 500 on server error', async () => {
        (commentService.getCommentsByPost as jest.Mock).mockRejectedValue(new Error(GENERAL_ERRORS.UNKNOWN));

        const res = await request(app)
            .get('/comment/101')
            .set('Authorization', `Bearer ${token}`); // Provide Authorization header

        expect(res.status).toBe(HTTP.INTERNAL_ERROR.code);
        expect(res.body).toEqual({ message: GENERAL_ERRORS.UNKNOWN });
    });
});