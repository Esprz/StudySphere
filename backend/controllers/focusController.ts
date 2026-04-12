import { Request, Response } from 'express';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';
import * as focusService from '../services/focusService';
import { eventService } from '../services/eventService';

export const startFocus = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    const { goal_id, tags, sourceTrigger, start } = req.body;

    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const focusSession = await focusService.startFocus({
      user_id,
      goal_id,
      tags,
      sourceTrigger,
      start: start ? new Date(start) : undefined,
    });

    setImmediate(async () => {
      try {
        await eventService.trackFocusStarted(
          focusSession.ft_id,
          user_id,
          focusSession.goal_id ?? undefined,
          focusSession.tags,
          focusSession.sourceTrigger ?? undefined,
          req.sessionId
        );
      } catch (error) {
        console.error('Focus start tracking failed:', error);
      }
    });

    res.status(HTTP.CREATED.code).json(focusSession);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const endFocus = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    const { ft_id } = req.params;
    const end = req.body?.end ? new Date(req.body.end) : new Date();

    if (!user_id || !ft_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const updated = await focusService.endFocus({ ft_id, user_id, end });
    if (updated.count === 0) {
      res.status(HTTP.NOT_FOUND.code).json({ message: GENERAL_ERRORS.UNKNOWN });
      return;
    }

    const durationMs = req.body?.start
      ? Math.max(0, end.getTime() - new Date(req.body.start).getTime())
      : undefined;

    setImmediate(async () => {
      try {
        await eventService.trackFocusEnded(
          ft_id,
          user_id,
          req.body?.goal_id,
          durationMs,
          req.sessionId
        );
      } catch (error) {
        console.error('Focus end tracking failed:', error);
      }
    });

    res.status(HTTP.OK.code).json({ message: 'Focus session ended.' });
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getFocusSessions = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;

    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const sessions = await focusService.getFocusSessions(user_id);
    res.status(HTTP.OK.code).json(sessions);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
