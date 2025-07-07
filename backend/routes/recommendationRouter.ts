import { Router } from 'express';
import { getSimilarPosts } from '../controllers/recommendationController';
import auth from '../middleware/authMiddleware';

const router = Router();

router.get('/similar-posts/:post_id', auth, getSimilarPosts);

export default router;