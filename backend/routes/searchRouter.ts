import { Router } from 'express';
import { searchPosts } from '../controllers/searchController';
import { trackSearch } from '../middleware/eventTracking.middleware';

const router = Router();

router.get('/', trackSearch, searchPosts);



export default router; 
