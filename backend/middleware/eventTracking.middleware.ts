import { Request, Response, NextFunction } from 'express';
import { eventService } from '../services/eventService';

export const trackPageView = (req: Request, res: Response, next: NextFunction) => {
    const userId = req.userId;
    const postId = req.params.post_id;
    const sessionId = req.sessionID || req.headers['x-session-id'] as string;
    
    if (userId && postId) {
        setImmediate(async () => {
            try {
                await eventService.trackPostViewed(postId, userId, sessionId);
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
    const sessionId = req.sessionID || req.headers['x-session-id'] as string;
    
    if (userId && query) {
        setImmediate(async () => {
            try {
                await eventService.trackSearchPerformed(userId, query, sessionId);
            } catch (error) {
                console.error('Search tracking failed:', error);
            }
        });
    }
    
    next();
};