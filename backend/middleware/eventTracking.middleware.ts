import { Request, Response, NextFunction } from 'express';
import { eventService } from '../services/eventService';

const parseOptionalInt = (value: unknown): number | undefined => {
    if (typeof value !== 'string' || value.trim() === '') {
        return undefined;
    }

    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? undefined : parsed;
};

export const trackPageView = (req: Request, res: Response, next: NextFunction) => {
    const userId = req.userId;
    const postId = req.params.post_id;
    const sessionId = req.sessionId;
    const dwellMs = parseOptionalInt(req.query.dwellMs);
    const position = parseOptionalInt(req.query.position);
    
    if (userId && postId) {
        setImmediate(async () => {
            try {
                await eventService.trackPostViewed(
                    postId,
                    userId,
                    sessionId,
                    dwellMs,
                    position
                );
            } catch (error) {
                console.error('Page view tracking failed:', error);
            }
        });
    }
    
    next();
};

export const trackSearch = (req: Request, res: Response, next: NextFunction) => {
    const userId = req.userId;
    const query = req.query.q as string;
    const sessionId = req.sessionId;
    
    if (userId && query) {
        setImmediate(async () => {
            try {
                await eventService.trackSearchPerformed(userId, query, 0, sessionId);
            } catch (error) {
                console.error('Search tracking failed:', error);
            }
        });
    }
    
    next();
};
