import { Request, Response } from 'express';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';
import * as taskService from '../services/taskService';
import { eventService } from '../services/eventService';

export const createTask = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    const { content, goal_id, due_at } = req.body;

    if (!user_id || !content) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const task = await taskService.createTask({
      user_id,
      content,
      goal_id,
      due_at: due_at ? new Date(due_at) : undefined,
    });

    setImmediate(async () => {
      try {
        await eventService.trackTaskAdded(
          task.task_id,
          user_id,
          task.content,
          task.goal_id ?? undefined,
          req.sessionId
        );
      } catch (error) {
        console.error('Task create tracking failed:', error);
      }
    });

    res.status(HTTP.CREATED.code).json(task);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const completeTask = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    const { task_id } = req.params;
    const { goal_id } = req.body;

    if (!user_id || !task_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const updated = await taskService.completeTask(task_id, user_id);
    if (updated.count === 0) {
      res.status(HTTP.NOT_FOUND.code).json({ message: GENERAL_ERRORS.UNKNOWN });
      return;
    }

    setImmediate(async () => {
      try {
        await eventService.trackTaskCompleted(
          task_id,
          user_id,
          goal_id,
          req.sessionId
        );
      } catch (error) {
        console.error('Task completion tracking failed:', error);
      }
    });

    res.status(HTTP.OK.code).json({ message: 'Task completed.' });
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getTasks = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;

    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const tasks = await taskService.getTasks(user_id);
    res.status(HTTP.OK.code).json(tasks);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
