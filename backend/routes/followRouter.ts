import express from 'express';
import {
  createFollow,
  deleteFollow,
  getFollowers,
  getFollowees,
  getSuggestedToFollow,
} from '../controllers/followController';
import auth from '../middleware/authMiddleware';

const router = express.Router();

router.post('/:followee_username', auth, createFollow);
router.delete('/:followee_username', auth, deleteFollow);
router.get('/followers', auth, getFollowers);
router.get('/followees', auth, getFollowees);
router.get('/suggested_to_follow', auth, getSuggestedToFollow);

export default router;
