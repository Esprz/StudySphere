import { Request, Response } from 'express';
import * as saveService from '../services/saveService';
import { HTTP } from '../constants/httpStatus';
import { SAVE_ERRORS, GENERAL_ERRORS } from '../constants/errorMessages';

export const savePost = async (req: Request, res: Response): Promise<void> => {
  try {
    const { post_id } = req.params;
    const { user_id } = req.body;

    if (!post_id || !user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const save = await saveService.savePost(post_id, user_id);

    if (!save) {
      res.status(HTTP.CONFLICT.code).json({ message: SAVE_ERRORS.ALREADY_SAVED });
      return;
    }

    res.status(HTTP.CREATED.code).json(save);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const deleteSave = async (req: Request, res: Response): Promise<void> => {
  try {
    const { save_id } = req.params;
    await saveService.deleteSave(save_id);
    res.status(HTTP.OK.code).json({ message: 'Save deleted successfully.' });
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getSavedPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    const { user_id } = req.params;
    const posts = await saveService.getSavedPosts(user_id);
    res.status(HTTP.OK.code).json(posts);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
