import { Router } from 'express';
import { getCurrentUser, logout, refreshTokens, signIn, signUp } from '../controllers/authController';
import auth from '../middleware/auth';

const router = Router();

router.post('/sign-in', signIn);
router.post('/sign-up', signUp);
router.get('/user',auth, getCurrentUser);
router.post('/logout', logout);
router.post('/refresh-token', refreshTokens);

export default router; 
