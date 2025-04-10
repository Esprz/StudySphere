import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import prisma from 'prisma';
import { Request, Response } from 'express';
import * as authService from '../services/authService';
import { HTTP } from '../constants/httpStatus';
import { USER_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';

// Handles user sign-in, generates tokens, and sets the refresh token as an httpOnly cookie
export const signIn = async (req: any, res: any) => {
    try {
        const { email, password } = req.body;
        const { user, accessToken, refreshToken } = await authService.signIn(email, password);

        // Set refreshToken in httpOnly cookie for security
        res.cookie('refreshToken', refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        });

        // Return user data and accessToken
        res.status(HTTP.OK.code).json({ user, accessToken });

    } catch (error: any) {
        if (error.message === USER_ERRORS.NOT_FOUND || error.message === GENERAL_ERRORS.MISSING_FIELDS) {
            res.status(HTTP.BAD_REQUEST.code).json({ message: error.message });
        } else {
            res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
        }
    }
};

// sign up and returns user and token
export const signUp = async (req: any, res: any) => {
    try {
        const { username, display_name, email, password, bio = null, avatar_url = null } = req.body;
        const { user, accessToken, refreshToken } = await authService.signUp(username, display_name, email, password, bio, avatar_url);

        // Set refreshToken in httpOnly cookie for security
        res.cookie('refreshToken', refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        });

        // Return user data and accessToken
        res.status(HTTP.OK.code).json({ user, accessToken });

    } catch (error: any) {
        if (error.message === USER_ERRORS.ALREADY_EXISTS) {
            res.status(HTTP.CONFLICT.code).json({ message: error.message });
        } else {
            console.error('Error in signUp:', error);
            console.log('Error message:', error.message);
            res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
        }
    }
};
export const getCurrentUser = async (req: Request, res: Response): Promise<void> => {
    try {
        const userId = req.userId;
        console.log('User ID from middleware:', userId); // Debugging line
        if (!userId) {
            res.status(HTTP.UNAUTHORIZED.code).json({ message: USER_ERRORS.NOT_FOUND });
            return; // Ensure the function exits after sending a response
        }

        const user = await authService.getCurrentUser(userId);

        if (!user) {
            res.status(HTTP.NOT_FOUND.code).json({ message: USER_ERRORS.NOT_FOUND });
            return; // Ensure the function exits after sending a response
        }

        res.status(HTTP.OK.code).json(user);
    } catch (error: any) {
        console.error('Error in getCurrentUser:', error);
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const logout = async (req: Request, res: Response) => {
    try {
        //console.log('Logout request received'); // Debugging line
        const refreshToken = req.cookies.refreshToken; // Get refresh token from httpOnly cookie
        //console.log('Logout refreshToken:', refreshToken); // Debugging line
        if (!refreshToken) {
            res.status(HTTP.UNAUTHORIZED.code).json({ message: USER_ERRORS.REFRESHTOKEN_NOT_FOUND });
            return;
        }
        //console.log('Logout refreshToken:', refreshToken); // Debugging line

        await authService.logout(refreshToken);

        //console.log('Logout successful'); // Debugging line

        res.clearCookie('refreshToken', {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
        });

        //console.log('Cookie cleared'); // Debugging line

        res.status(HTTP.NO_CONTENT.code).send();

    } catch (error: any) {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const refreshTokens = async (req: Request, res: Response) => {
    try {
        const refreshToken = req.cookies.refreshToken; // Get refresh token from httpOnly cookie
        if (!refreshToken) {
            res.status(HTTP.UNAUTHORIZED.code).json({ message: USER_ERRORS.REFRESHTOKEN_NOT_FOUND });
            return;
        }

        const { accessToken, refreshToken: newRefreshToken } = await authService.refreshTokens(refreshToken);

        res.cookie('refreshToken', newRefreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        });

        res.status(HTTP.OK.code).json({ accessToken });

    } catch (error: any) {
        res.status(HTTP.UNAUTHORIZED.code).json({ message: error.message });
    }
};