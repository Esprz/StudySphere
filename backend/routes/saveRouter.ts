import { Router } from 'express';
import {
    savePost,
    deleteSave,
    getSavedPosts,
  } from '../controllers/saveController';
  import auth from '../middleware/authMiddleware';

const router = Router();


router.post('/:post_id', auth, savePost);
router.delete('/:save_id', auth, deleteSave);
router.get('/', auth, getSavedPosts);


export default router; 
