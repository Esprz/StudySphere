import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { persistSessionContext } from '../utils/redis';

export const attachSessionContext = (
    req: Request,
    res: Response,
    next: NextFunction
) => {
    const incomingHeader = req.headers['x-session-id'];
    const sessionId =
        typeof incomingHeader === 'string' && incomingHeader.trim() !== ''
            ? incomingHeader
            : uuidv4();

    req.sessionId = sessionId;
    res.setHeader('x-session-id', sessionId);

    setImmediate(async () => {
        await persistSessionContext(sessionId);
    });

    next();
};
