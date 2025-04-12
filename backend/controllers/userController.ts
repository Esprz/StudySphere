import { Request, Response } from 'express';
import * as userService from '../services/userService';
import { HTTP } from '../constants/httpStatus';
import { USER_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';


export const getUserInfo = async (req: Request, res: Response): Promise<void> => {
    try {
        const { username } = req.body;
        if (!username) {
            res.status(HTTP.UNAUTHORIZED.code).json({ message: USER_ERRORS.NOT_FOUND });
            return; // Ensure the function exits after sending a response
        }

        const user = await userService.getUserInfo(username);
        if (!user) {
            res.status(HTTP.NOT_FOUND.code).json({ message: USER_ERRORS.NOT_FOUND });
            return; // Ensure the function exits after sending a response
        }

        res.status(HTTP.OK.code).json(user);
    } catch (error: any) {
        console.error('Error in getUserInfo:', error);
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

