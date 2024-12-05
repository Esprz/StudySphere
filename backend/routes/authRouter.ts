import { Router } from 'express';
import { getCurrentUser, signIn, signUp } from '../controllers/authController';
import auth from '../middleware/auth';

const router = Router();

router.post('/sign-in', signIn);
router.post('/sign-up', signUp);
router.get('/user',auth, getCurrentUser);


export default router; 
