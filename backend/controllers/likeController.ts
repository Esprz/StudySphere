import { Request, Response } from 'express';
import * as likeService from '../services/likeService';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS, LIKE_ERRORS } from '../constants/errorMessages';

export const likePost = async (req: Request, res: Response): Promise<void> => {
  try {
    const { post_id } = req.params;
    const { user_id } = req.body;

    if (!post_id || !user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
    }

    const like = await likeService.likePost(post_id, user_id);

    if (!like) {
      res.status(HTTP.CONFLICT.code).json({ message: LIKE_ERRORS.ALREADY_LIKED });
    }

    res.status(HTTP.CREATED.code).json(like);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const deleteLike = async (req: Request, res: Response): Promise<void> => {
  try {
    const { like_id } = req.params;
    await likeService.deleteLike(like_id);
    res.status(HTTP.OK.code).json({ message: 'Like deleted.' });
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getLikedPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    const { user_id } = req.params;
    const posts = await likeService.getLikedPosts(user_id);
    res.status(HTTP.OK.code).json(posts);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
