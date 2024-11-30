import { Router } from 'express';
import {createPost, updatePost, deletePost, likePost, deleteLike, savePost, deleteSave, getPostById, getLikedPosts, getSavedPosts, getAllPosts } from '../controllers/postController';

const router = Router();

router.post('/', createPost);
router.patch('/:post_id', updatePost);
router.delete('/:post_id', deletePost);
router.get('/', getAllPosts);
router.get('/:post_id', getPostById);


router.post('/:post_id/like/', likePost);
router.delete('/:post_id/like/:like_id', deleteLike);

router.post('/:post_id/save/', savePost);
router.delete('/:post_id/save/:save_id', deleteSave);


router.get('/:user_id/likes/', getLikedPosts);
router.get('/:user_id/saves/', getSavedPosts);


export default router; 
