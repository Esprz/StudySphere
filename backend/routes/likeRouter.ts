import { Router } from 'express';
import {
    likePost,
    deleteLike,
    getLikedPosts,
  } from '../controllers/likeController';
import auth from '../middleware/authMiddleware';

const router = Router();

router.post('/:post_id', auth, likePost);
router.delete('/:like_id', auth, deleteLike);
router.get('/', auth, getLikedPosts);


export default router; 
