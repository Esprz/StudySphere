import express from 'express';
import auth from '../middleware/authMiddleware';
import {
  completeTask,
  createTask,
  getTasks,
} from '../controllers/taskController';

const router = express.Router();

router.post('/', auth, createTask);
router.patch('/:task_id/complete', auth, completeTask);
router.get('/', auth, getTasks);

export default router;
