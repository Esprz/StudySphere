import { Router } from 'express';
import { createPost, updatePost, deletePost, getPostById, getAllPosts, getRecentPosts, getPaginatedPosts, getPostByUser, getFolloweePosts, getFriendsPosts} from '../controllers/postController';
import auth from '../middleware/authMiddleware';

const router = Router();

router.post('/', auth, createPost);
router.patch('/:post_id', auth, updatePost);
router.delete('/:post_id', auth, deletePost);

router.get('/', getAllPosts);
router.get('/recent', getRecentPosts);
router.get('/:post_id', getPostById);
router.post('/by_user', getPostByUser);
router.post('/infinite', getPaginatedPosts);
router.get('/followee', auth, getFolloweePosts);
router.get('/friends', auth, getFriendsPosts);

export default router; 
