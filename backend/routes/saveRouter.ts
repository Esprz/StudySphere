import { Router } from 'express';
import {
    savePost,
    deleteSave,
    getSavedPosts,
  } from '../controllers/saveController';
  import auth from '../middleware/auth';

const router = Router();


router.post('/:post_id', auth, savePost);
router.delete('/:post_id/save/:save_id', auth, deleteSave);
router.get('/:user_id', auth, getSavedPosts);


export default router; 
