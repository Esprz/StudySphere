import { Request, Response } from 'express';
import * as likeService from '../services/likeService';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS, LIKE_ERRORS } from '../constants/errorMessages';
import { LIKE_SUCCESS } from '../constants/successMessages';

export const likePost = async (req: Request, res: Response): Promise<void> => {
  try {
    const { post_id } = req.params;
    const user_id = req.userId;

    if (!post_id || !user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const like = await likeService.likePost(post_id, user_id);

    if (!like) {
      res.status(HTTP.CONFLICT.code).json({ message: LIKE_ERRORS.ALREADY_LIKED });
      return;
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
    res.status(HTTP.OK.code).json({ message: LIKE_SUCCESS.DELETED });
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getLikedPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }
    const posts = await likeService.getLikedPosts(user_id);
    res.status(HTTP.OK.code).json(posts);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
