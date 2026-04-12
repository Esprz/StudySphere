import { Router } from 'express';
import { searchPosts } from '../controllers/searchController';
import { attachUserIfAuthenticated } from '../middleware/authMiddleware';

const router = Router();

router.get('/', attachUserIfAuthenticated, searchPosts);



export default router; 
