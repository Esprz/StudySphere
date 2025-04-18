import { Request, Response } from 'express';
import * as postService from '../services/postService';
import { HTTP } from '../constants/httpStatus';
import { POST_ERRORS, GENERAL_ERRORS, USER_ERRORS } from '../constants/errorMessages';


export const getAllPosts = async (req: Request, res: Response) => {
    try {
        const posts = await postService.getAllPosts();
        res.status(HTTP.OK.code).json(posts);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const getPostById = async (req: Request, res: Response) => {
    try {
        const { post_id } = req.params;
        const post = await postService.getPostById(post_id);

        if (!post) {
            res.status(HTTP.NOT_FOUND.code).json({ message: POST_ERRORS.NOT_FOUND });
            return;
        }

        res.status(HTTP.OK.code).json(post);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const getRecentPosts = async (req: Request, res: Response) => {
    try {
        const posts = await postService.getRecentPosts();
        res.status(HTTP.OK.code).json(posts);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const getPostByUser = async (req: Request, res: Response) => {
    try {
        const { username } = req.body;
        const post = await postService.getPostByUser(username);

        if (!post) {
            res.status(HTTP.NOT_FOUND.code).json({ message: POST_ERRORS.NOT_FOUND });
            return;
        }

        res.status(HTTP.OK.code).json(post);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const getFolloweePosts = async (req: Request, res: Response) => {
    try {
        const user_id = req.userId;
        if (!user_id) {
            res.status(HTTP.UNAUTHORIZED.code).json({ message: POST_ERRORS.MISSING_FIELDS });
            return;
        }
        const post = await postService.getFolloweePosts(user_id);
        
        if (!post) {
            res.status(HTTP.NOT_FOUND.code).json({ message: POST_ERRORS.NOT_FOUND });
            return;
        }

        res.status(HTTP.OK.code).json(post);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const getFriendsPosts = async (req: Request, res: Response) => {
    try {
        const user_id = req.userId;
        if (!user_id) {
            res.status(HTTP.UNAUTHORIZED.code).json({ message: POST_ERRORS.MISSING_FIELDS });
            return;
        }
        const post = await postService.getFriendsPosts(user_id);

        if (!post) {
            res.status(HTTP.NOT_FOUND.code).json({ message: POST_ERRORS.NOT_FOUND });
            return;
        }

        res.status(HTTP.OK.code).json(post);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const getPaginatedPosts = async (req: Request, res: Response) => {
    try {
        const page = parseInt(req.query.page as string) || 0;
        const posts = await postService.getPaginatedPosts(page);
        res.status(HTTP.OK.code).json(posts);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};


export const createPost = async (req: Request, res: Response) => {
    try {
        const { title, content, image, extra, user_id } = req.body;

        if (!title || !content || !user_id) {
            res.status(HTTP.BAD_REQUEST.code).json({ message: POST_ERRORS.MISSING_FIELDS });
            return;
        }

        const post = await postService.createPost({ title, content, image, extra, user_id });
        res.status(HTTP.CREATED.code).json(post);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const updatePost = async (req: Request, res: Response) => {
    try {
        const { post_id } = req.params;
        const post = await postService.updatePost(post_id, req.body);
        res.status(HTTP.OK.code).json(post);
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};

export const deletePost = async (req: Request, res: Response) => {
    try {
        const { post_id } = req.params;
        await postService.deletePost(post_id);
        res.status(HTTP.OK.code).json({ message: 'Post deleted successfully.' });
    } catch {
        res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
};


