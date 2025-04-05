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
    const refreshToken = await generateRefreshToken(user.user_id);

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
    const refreshToken = await generateRefreshToken(user.user_id);

    return { user, accessToken, refreshToken };
};

export const logout = async (refreshToken: string) => {
    await prisma.token.delete({ where: { token: refreshToken } });
};

export const getCurrentUser = async (userId: string) => {
    return prisma.user.findUnique({
        where: { user_id: userId },
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

    const storedToken = await prisma.token.findUnique({ where: { token: refreshToken } });
    if (!storedToken || storedToken.expires_at < new Date()) {
        throw new Error('Invalid or expired refresh token');
    }

    const accessToken = generateAccessToken((decoded as any).userId);
    const newRefreshToken = await generateRefreshToken((decoded as any).userId);

    await prisma.token.delete({ where: { token: refreshToken } });

    return { accessToken, refreshToken: newRefreshToken };
};