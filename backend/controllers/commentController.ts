import { Request, Response } from 'express';
import * as commentService from '../services/commentService';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';
import { COMMENT_SUCCESS } from '../constants/successMessages';
export const createComment = async (req: Request, res: Response): Promise<void> => {
    try {
      const { post_id } = req.params;
      const user_id = req.userId;
      const { content, parent_id } = req.body;
  
      if (!post_id || !user_id || !content) {
        res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
        return;
      }
  
      const comment = await commentService.createComment(post_id, user_id, content, parent_id);
      res.status(HTTP.CREATED.code).json(comment);
    } catch {
      res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
  };
  
  export const deleteComment = async (req: Request, res: Response): Promise<void> => {
    try {
      const { comment_id } = req.params;
      await commentService.deleteComment(comment_id);
      res.status(HTTP.OK.code).json({ message: COMMENT_SUCCESS.DELETED });
    } catch {
      res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
  };
  
  export const getCommentsByPost = async (req: Request, res: Response): Promise<void> => {
    try {
      const { post_id } = req.params;
      const comments = await commentService.getCommentsByPost(post_id);
      res.status(HTTP.OK.code).json(comments);
    } catch {
      res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
    }
  };