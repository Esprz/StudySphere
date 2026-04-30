import { Router } from 'express';
import {
  getFeed,
  getSimilarPosts,
  getUserRecommendations,
} from '../controllers/recommendationController';
import auth from '../middleware/authMiddleware';

const router = Router();

router.get('/feed', auth, getFeed);
router.get('/users', auth, getUserRecommendations);
router.get('/similar-posts/:post_id', auth, getSimilarPosts);

export default router;
