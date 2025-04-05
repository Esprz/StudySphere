import pool from '../config/db';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import prisma from 'prisma';
import { Request, Response } from 'express';
import * as authService from '../services/authService';
import { HTTP } from '../constants/httpStatus';
import { USER_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';

// return sign in and returns user and token
export const signIn = async (req: any, res: any) => {
    try {
        const { email, password } = req.body;
        const result = await authService.signIn(email, password);
        res.status(HTTP.OK.code).json(result);
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
        const result = await authService.signUp(username, display_name, email, password, bio, avatar_url);
        res.status(HTTP.CREATED.code).json(result);
    } catch (error: any) {
        if (error.message === USER_ERRORS.ALREADY_EXISTS) {
            res.status(HTTP.CONFLICT.code).json({ message: error.message });
        } else {
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
        const { refreshToken } = req.body;
        await authService.logout(refreshToken);
        res.status(HTTP.NO_CONTENT.code).send();
    } catch (error: any) {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const refreshTokens = async (req: Request, res: Response) => {
    try {
        const { refreshToken } = req.body;
        const result = await authService.refreshTokens(refreshToken);
        res.status(HTTP.OK.code).json(result);
    } catch (error: any) {
        res.status(HTTP.UNAUTHORIZED.code).json({ message: error.message });
    }
};