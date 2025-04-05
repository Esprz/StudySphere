import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
dotenv.config();

// Validate environment variables
const accessTokenSecret = process.env.ACCESS_TOKEN_SECRET;
const refreshTokenSecret = process.env.REFRESH_TOKEN_SECRET;

if (!accessTokenSecret || !refreshTokenSecret) {
    throw new Error('JWT secrets are not defined in environment variables');
}

// Use constants for expiresIn
const ACCESS_TOKEN_EXPIRE = '1h'; // 1 hour
const REFRESH_TOKEN_EXPIRE = '7d'; // 7 days

export const generateAccessToken = (userId: string) => {
    return jwt.sign(
        { userId },
        accessTokenSecret,
        { expiresIn: ACCESS_TOKEN_EXPIRE, algorithm: 'HS256' }
    );
};

export const generateRefreshToken = (userId: string) => {
    return jwt.sign(
        { userId },
        refreshTokenSecret,
        { expiresIn: REFRESH_TOKEN_EXPIRE, algorithm: 'HS256' }
    );
};

export const verifyAccessToken = (token: string) => {
    return jwt.verify(token, accessTokenSecret, { algorithms: ['HS256'] });
};

export const verifyRefreshToken = (token: string) => {
    return jwt.verify(token, refreshTokenSecret, { algorithms: ['HS256'] });
};