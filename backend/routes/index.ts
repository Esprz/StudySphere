import express from 'express';

import postsRouter from './postRouter';
import authRouter from './authRouter';
import saveRouter from './saveRouter';
import likeRouter from './likeRouter';
import searchRouter from './searchRouter';
import commentRouter from './commentRouter';
import followRouter from './followRouter';
import userRouter from './userRouter';

const router = express.Router();

router.use('/post', postsRouter);
router.use('/auth', authRouter);
router.use('/save', saveRouter); 
router.use('/like', likeRouter);
router.use('/search', searchRouter);
router.use('/comment', commentRouter);
router.use('/follow', followRouter);
router.use('/user', userRouter);

export default router;
