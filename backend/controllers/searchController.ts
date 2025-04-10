import { Request, Response } from 'express';
import * as postService from '../services/postService';
import { HTTP } from '../constants/httpStatus';
import { POST_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';
export const searchPosts = async (req: Request, res: Response) => {
    try {
        const { q } = req.query;
        if (!q || typeof q !== 'string' || q == '') {
            res.status(HTTP.BAD_REQUEST.code).json({ message: POST_ERRORS.MISSING_FIELDS });
            return;
        }

        const posts = await postService.searchPosts(q);
        res.status(HTTP.OK.code).json(posts);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};