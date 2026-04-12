import { Router } from 'express';
import { searchPosts } from '../controllers/searchController';
import { trackSearch } from '../middleware/eventTracking.middleware';
import { attachUserIfAuthenticated } from '../middleware/authMiddleware';

const router = Router();

router.get('/', attachUserIfAuthenticated, trackSearch, searchPosts);



export default router; 
