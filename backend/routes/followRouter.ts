import express from 'express';
import {
  createFollow,
  deleteFollow,
  getFollowers,
  getFollowees,
} from '../controllers/followController';

const router = express.Router();

router.post('/:followee_id/follow', createFollow);
router.delete('/follow/:follow_id', deleteFollow);
router.get('/followers/:user_id', getFollowers);
router.get('/followees/:user_id', getFollowees);

export default router;
