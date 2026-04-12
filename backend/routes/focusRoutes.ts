import express from 'express';
import auth from '../middleware/authMiddleware';
import {
  endFocus,
  getFocusSessions,
  startFocus,
} from '../controllers/focusController';

const router = express.Router();

router.post('/start', auth, startFocus);
router.post('/:ft_id/end', auth, endFocus);
router.get('/', auth, getFocusSessions);

export default router;
