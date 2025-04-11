import express from 'express';
import {
  createFollow,
  deleteFollow,
  getFollowers,
  getFollowees,
} from '../controllers/followController';
import auth from '../middleware/authMiddleware';

const router = express.Router();

router.post('/:followee_id', auth, createFollow);
router.delete('/:follow_id', auth, deleteFollow);
router.get('/followers', auth, getFollowers);
router.get('/followees', auth, getFollowees);

export default router;
