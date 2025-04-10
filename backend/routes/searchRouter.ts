import { Router } from 'express';
import { searchPosts } from '../controllers/searchController';

const router = Router();

router.get('/', searchPosts);



export default router; 
