import { Router } from 'express';
import { createPost, updatePost, deletePost, getPostById, getAllPosts, getRecentPosts, } from '../controllers/postController';
import auth from '../middleware/auth';

const router = Router();

router.post('/search', searchPosts);



export default router; 
