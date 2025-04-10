import bcrypt from 'bcrypt';
import { PrismaClient } from '@prisma/client';
import { generateAccessToken, generateRefreshToken, verifyRefreshToken } from '../utils/jwt';
import { USER_ERRORS } from '../constants/errorMessages';

const prisma = new PrismaClient();

export const signUp = async (
    username: string, display_name: string, email: string, 
    password: string, bio: string, avatar_url: string) => {

    const existingUser = await prisma.user.findUnique({ where: { email } });
    if (existingUser) {
        throw new Error(USER_ERRORS.ALREADY_EXISTS);
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const user = await prisma.user.create({
        data: {
            username,
            display_name,
            email,
            password_hash: hashedPassword,
            bio,
            avatar_url
        },
    });

    const accessToken = generateAccessToken(user.user_id);
    const refreshToken = generateRefreshToken(user.user_id);
    
    await prisma.token.create({
        data: {
            token: refreshToken,
            user_id: user.user_id,
            expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        },
    });

    return { user, accessToken, refreshToken };
};

export const signIn = async (email: string, password: string) => {
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user) {
        throw new Error(USER_ERRORS.NOT_FOUND);
    }

    const isPasswordValid = await bcrypt.compare(password, user.password_hash);
    if (!isPasswordValid) {
        throw new Error('Invalid credentials');
    }

    const accessToken = generateAccessToken(user.user_id);
    const refreshToken = generateRefreshToken(user.user_id);
    await prisma.token.create({
        data: {
            token: refreshToken,
            user_id: user.user_id,
            expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        },
    });

    return { user, accessToken, refreshToken };
};

export const logout = async (refreshToken: string) => {
    return await prisma.token.delete({ where: { token: refreshToken } });
};

export const getCurrentUser = async (user_id: string) => {
    return prisma.user.findUnique({
        where: { user_id: user_id },
        select: {
            user_id: true,
            username: true,
            display_name: true,
            email: true,
            bio: true,
            avatar_url: true,
            created_at: true,
            updated_at: true,
        },
    });
};

export const refreshTokens = async (refreshToken: string) => {
    const decoded = verifyRefreshToken(refreshToken);
    const userId = (decoded as any).userId;
    
    const storedToken = await prisma.token.findUnique({ where: { token: refreshToken } });
    if (!storedToken || storedToken.expires_at < new Date()) {
        throw new Error('Invalid or expired refresh token');
    }
    if (storedToken.user_id !== userId) {
        throw new Error('Refresh token does not belong to this user');
    }

    const newAccessToken = generateAccessToken((decoded as any).userId);
    const newRefreshToken = generateRefreshToken((decoded as any).userId);

    await prisma.token.delete({ where: { token: refreshToken } });
    await prisma.token.create({
        data: {
            token: newRefreshToken,
            user_id: (decoded as any).userId,
            expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        },
    });
    return { accessToken: newAccessToken, refreshToken: newRefreshToken };
};