import { Request, Response } from 'express';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';
import prisma from '../utils/prisma';
import { readCacheValue } from '../utils/redis';
import {
  getRecommendedFeedFromRecommender,
  getRecommendedUsers,
} from '../services/recommendationService';

const REC_FEED_PREFIX = 'rec:feed:';
const DEFAULT_LIMIT = 20;

export const getFeed = async (req: Request, res: Response): Promise<void> => {
  try {
    const userId = req.userId;
    if (!userId) {
      res.status(HTTP.UNAUTHORIZED.code).json({ message: 'Unauthorized' });
      return;
    }
    const limit = Math.min(
      parseInt(req.query.limit as string, 10) || DEFAULT_LIMIT,
      100
    );

    try {
      const cached = await readCacheValue(`${REC_FEED_PREFIX}${userId}`);
      if (cached) {
        const parsed = JSON.parse(cached);
        const postIds: string[] = Array.isArray(parsed)
          ? parsed
              .slice(0, limit)
              .map((entry: string | { post_id?: string; item_id?: string }) =>
                typeof entry === 'string' ? entry : entry.post_id || entry.item_id
              )
              .filter((postId): postId is string => Boolean(postId))
          : [];

        if (postIds.length > 0) {
          const posts = await prisma.post.findMany({
            where: { post_id: { in: postIds } },
            include: {
              user: { select: { user_id: true, username: true, avatar_url: true } },
            },
          });

          const postById = new Map(posts.map((post) => [post.post_id, post]));
          const orderedPosts = postIds
            .map((postId) => postById.get(postId))
            .filter((post): post is NonNullable<typeof post> => Boolean(post));

          res.status(HTTP.OK.code).json({ posts: orderedPosts, source: 'recommended' });
          return;
        }
      }
    } catch (err) {
      console.error('Redis read failed, falling back:', err);
    }

    const recommenderResult = await getRecommendedFeedFromRecommender(userId, limit);
    if (
      recommenderResult &&
      Array.isArray(recommenderResult.posts) &&
      recommenderResult.posts.length > 0
    ) {
      res.status(HTTP.OK.code).json({ posts: recommenderResult.posts, source: 'recommender' });
      return;
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

export const getUserRecommendations = async (
  req: Request,
  res: Response
): Promise<void> => {
  try {
    const userId = req.userId;
    if (!userId) {
      res.status(HTTP.UNAUTHORIZED.code).json({ message: 'Unauthorized' });
      return;
    }
    const limit = Math.min(
      parseInt(req.query.limit as string, 10) || 5,
      20
    );

    const result = await getRecommendedUsers(userId, limit);
    res.status(HTTP.OK.code).json(result);
  } catch (error) {
    console.error('Error fetching user recommendations:', error);
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};
