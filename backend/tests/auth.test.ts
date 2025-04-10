import request from 'supertest';
import express from 'express';
import cookieParser from 'cookie-parser';
import authRouter from '../routes/authRouter';
import * as authService from '../services/authService';
import { HTTP } from '../constants/httpStatus';
import { generateAccessToken } from '../utils/jwt';

// Mock the authService
jest.mock('../services/authService');

const app = express();
app.use(express.json());
app.use(cookieParser());
app.use('/auth', authRouter);

describe('Auth Routes', () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    test('POST /auth/sign-up should create a new user and return tokens', async () => {
        const newUser = {
            username: 'testuser',
            display_name: 'Test User',
            email: 'test@example.com',
            password: 'password123',
            bio: 'This is a test user',
            avatar_url: 'http://example.com/avatar.png',
        };

        const mockResponse = {
            user: { user_id: '1', ...newUser },
            accessToken: 'access-token',
            refreshToken: 'refresh-token',
        };

        (authService.signUp as jest.Mock).mockResolvedValue(mockResponse);

        const res = await request(app).post('/auth/sign-up').send(newUser);

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual({
            user: mockResponse.user,
            accessToken: mockResponse.accessToken,
        });
        expect(authService.signUp).toHaveBeenCalledWith(
            newUser.username,
            newUser.display_name,
            newUser.email,
            newUser.password,
            newUser.bio,
            newUser.avatar_url
        );
    });

    test('POST /auth/sign-in should return tokens for valid credentials', async () => {
        const credentials = { email: 'test@example.com', password: 'password123' };
        const mockResponse = {
            user: { user_id: '1', email: credentials.email },
            accessToken: 'access-token',
            refreshToken: 'refresh-token',
        };

        (authService.signIn as jest.Mock).mockResolvedValue(mockResponse);

        const res = await request(app).post('/auth/sign-in').send(credentials);

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual({
            user: mockResponse.user,
            accessToken: mockResponse.accessToken,
        });
        expect(authService.signIn).toHaveBeenCalledWith(credentials.email, credentials.password);
    });

    test('GET /auth/logout should log out the user and clear refreshToken cookie', async () => {
        (authService.logout as jest.Mock).mockResolvedValue(undefined);

        const res = await request(app)
            .get('/auth/logout')
            .set('Cookie', ['refreshToken=refresh-token']); // Simulate httpOnly cookie

        expect(res.status).toBe(HTTP.NO_CONTENT.code);
        expect(authService.logout).toHaveBeenCalledWith('refresh-token');
        expect(res.headers['set-cookie'][0]).toMatch(/refreshToken=;/); // Ensure cookie is cleared
    });

    test('GET /auth/refresh-token should return new tokens', async () => {
        const mockResponse = {
            accessToken: 'new-access-token',
            refreshToken: 'new-refresh-token',
        };

        (authService.refreshTokens as jest.Mock).mockResolvedValue(mockResponse);

        const res = await request(app)
            .get('/auth/refresh-token')
            .set('Cookie', ['refreshToken=refresh-token']); // Simulate httpOnly cookie

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual({ accessToken: mockResponse.accessToken });
        expect(authService.refreshTokens).toHaveBeenCalledWith('refresh-token');
        expect(res.headers['set-cookie'][0]).toMatch(/refreshToken=new-refresh-token/); // Ensure new cookie is set
    });

    test('GET /auth/user should return the current user with a valid token', async () => {
        const mockUser = { user_id: '1', username: 'testuser', email: 'test@example.com' };

        // Generate a valid token
        const token = generateAccessToken('1');

        // Mock the authService.getCurrentUser to return the mock user
        (authService.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);

        // Send the request with the Authorization header
        const res = await request(app)
            .get('/auth/user')
            .set('Authorization', `Bearer ${token}`);

        expect(res.status).toBe(HTTP.OK.code);
        expect(res.body).toEqual(mockUser);
        expect(authService.getCurrentUser).toHaveBeenCalledWith('1');
    });
});