import { Router } from 'express';
import auth from '../middleware/authMiddleware';
import { getUserInfo } from '../controllers/userController';

const router = Router();

router.post('/',auth, getUserInfo);

export default router; 
