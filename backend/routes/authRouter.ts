import { Router } from 'express';
import { getCurrentUser, logout, refreshTokens, signIn, signUp } from '../controllers/authController';
import auth from '../middleware/authMiddleware';

const router = Router();

router.post('/sign-in', signIn);
router.post('/sign-up', signUp);
router.get('/user',auth, getCurrentUser);
router.get('/logout', logout);
router.get('/refresh-token', refreshTokens);

export default router; 
