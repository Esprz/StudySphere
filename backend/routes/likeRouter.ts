import { Router } from 'express';
import {
    likePost,
    deleteLike,
    getLikedPosts,
  } from '../controllers/likeController';
import auth from '../middleware/authMiddleware';

const router = Router();

router.post('/:post_id/like/', auth, likePost);
router.delete('/like/:like_id', auth, deleteLike);
router.get('/:user_id', auth, getLikedPosts);


export default router; 
