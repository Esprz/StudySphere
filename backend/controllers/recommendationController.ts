import { Request, Response } from 'express';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';
import prisma from '../utils/prisma';
import redis, { isRedisConnected } from '../utils/redis';

const REC_FEED_PREFIX = 'rec:feed:';
const DEFAULT_LIMIT = 20;

export const getFeed = async (req: Request, res: Response): Promise<void> => {
  try {
    const userId = req.userId;
    const limit = Math.min(
      parseInt(req.query.limit as string, 10) || DEFAULT_LIMIT,
      100
    );

    if (isRedisConnected()) {
      try {
        const cached = await redis.get(`${REC_FEED_PREFIX}${userId}`);
        if (cached) {
          const postIds: string[] = JSON.parse(cached).slice(0, limit);
          if (postIds.length > 0) {
            const posts = await prisma.post.findMany({
              where: { post_id: { in: postIds } },
              include: {
                user: { select: { user_id: true, username: true, avatar_url: true } },
              },
              orderBy: { created_at: 'desc' },
            });
            res.status(HTTP.OK.code).json({ posts, source: 'recommended' });
            return;
          }
        }
      } catch (err) {
        console.error('Redis read failed, falling back:', err);
      }
    }

    const posts = await prisma.post.findMany({
      take: limit,
      orderBy: { created_at: 'desc' },
      include: {
        user: { select: { user_id: true, username: true, avatar_url: true } },
      },
    });

    res.status(HTTP.OK.code).json({ posts, source: 'chronological' });
  } catch (error) {
    console.error('Error fetching feed:', error);
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getSimilarPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    // Stub: returns empty for now. Will be implemented in Spec 5.
    res.status(HTTP.OK.code).json({ posts: [], source: 'stub' });
  } catch (error) {
    console.error('Error fetching similar posts:', error);
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
