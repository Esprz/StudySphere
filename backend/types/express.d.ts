// filepath: /home/sy/projects/personal/StudySphere/backend/types/express.d.ts
import { Request } from 'express';

declare global {
    namespace Express {
        interface Request {
            userId?: string; // Add the custom property
        }
    }
}