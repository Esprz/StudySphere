import bcrypt from 'bcrypt';
import { PrismaClient } from '@prisma/client';
import { generateAccessToken, generateRefreshToken, verifyRefreshToken } from '../utils/jwt';
import { USER_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';

const prisma = new PrismaClient();

export const getUserInfo = async (username: string) => {
    try {
        const user = await prisma.user.findUnique({
            where: { username: username },
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

        if (!user) {
            throw new Error(USER_ERRORS.NOT_FOUND);
        }

        return user;
    } catch (error: any) {
        console.error('Error in getUserInfo:', error);
        throw new Error(GENERAL_ERRORS.UNKNOWN);
    }
};
