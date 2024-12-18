import { Router } from 'express';
import { createPost, updatePost, deletePost, likePost, deleteLike, savePost, deleteSave, getPostById, getLikedPosts, getSavedPosts, getAllPosts, getRecentPosts } from '../controllers/postController';
import auth from '../middleware/auth';

const router = Router();

router.post('/', auth, createPost);
router.patch('/:post_id', auth, updatePost);
router.delete('/:post_id', auth, deletePost);
router.get('/', getAllPosts);
router.get('/recent', getRecentPosts);
router.get('/:post_id', getPostById);


router.post('/:post_id/like/', auth, likePost);
router.delete('/:post_id/like/:like_id', auth, deleteLike);

router.post('/:post_id/save/', auth, savePost);
router.delete('/:post_id/save/:save_id', auth, deleteSave);


router.get('/:user_id/likes/', auth, getLikedPosts);
router.get('/:user_id/saves/', auth, getSavedPosts);


export default router; 
