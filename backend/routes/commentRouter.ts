import express from 'express';
import {
  createComment,
  deleteComment,
  getCommentsByPost,
} from '../controllers/commentController';
import auth from '../middleware/authMiddleware';

const router = express.Router();

router.post('/:post_id', auth, createComment);
router.delete('/:comment_id', auth, deleteComment);
router.get('/:post_id', auth, getCommentsByPost);

export default router;
