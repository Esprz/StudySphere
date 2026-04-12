import { Router } from 'express';
import { createPost, updatePost, deletePost, getPostById, getAllPosts, getRecentPosts, getPaginatedPosts, getPostByUser, getFolloweePosts, getFriendsPosts} from '../controllers/postController';
import auth, { attachUserIfAuthenticated } from '../middleware/authMiddleware';
import { trackPageView } from '../middleware/eventTracking.middleware';

const router = Router();

router.post('/', auth, createPost);
router.patch('/:post_id', auth, updatePost);
router.delete('/:post_id', auth, deletePost);
router.get('/followee', auth, getFolloweePosts);
router.get('/friends', auth, getFriendsPosts);

router.get('/', getAllPosts);
router.get('/recent', getRecentPosts);
router.get('/:post_id', attachUserIfAuthenticated, trackPageView, getPostById);
router.post('/by_user', getPostByUser);
router.post('/infinite', getPaginatedPosts);

export default router; 
