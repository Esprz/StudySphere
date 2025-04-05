import express from 'express';
import {
  createComment,
  deleteComment,
  getCommentsByPost,
} from '../controllers/commentController';

const router = express.Router();

router.post('/:post_id', createComment);
router.delete('/:comment_id', deleteComment);
router.get('/:post_id', getCommentsByPost);

export default router;
