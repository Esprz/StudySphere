import prisma from '../utils/prisma';
import { readCacheValue } from '../utils/redis';

const USER_REC_PREFIX = 'rec:users:';
const RECOMMENDER_BASE_URL = process.env.RECOMMENDER_URL || 'http://localhost:8000';

type RecommendedUser = {
  user_id: string;
  username?: string;
  display_name?: string;
  avatar_url?: string | null;
  bio?: string | null;
  score?: number;
  source?: string;
};

type RecommendedFeedResponse = {
  posts: unknown[];
  metadata?: Record<string, unknown>;
};

async function fetchFromRecommender<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${RECOMMENDER_BASE_URL}${path}`);
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch (error) {
    console.warn('Recommender fetch failed:', error);
    return null;
  }
}

export async function getRecommendedFeedFromRecommender(
  userId: string,
  limit: number
): Promise<RecommendedFeedResponse | null> {
  return await fetchFromRecommender<RecommendedFeedResponse>(
    `/recommendations/${userId}?limit=${limit}`
  );
}

export const getRecommendedUsers = async (userId: string, limit: number = 5) => {
  try {
    const cached = await readCacheValue(`${USER_REC_PREFIX}${userId}`);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return {
          users: parsed.slice(0, limit),
          source: 'recommended_users',
        };
      }
    }
  } catch (error) {
    console.warn('User recommendation cache read failed:', error);
  }

  const recommenderResult = await fetchFromRecommender<{
    recommendations?: RecommendedUser[];
  }>(`/recommendations/users/${userId}?limit=${limit}`);
  if (
    recommenderResult &&
    Array.isArray(recommenderResult.recommendations) &&
    recommenderResult.recommendations.length > 0
  ) {
    return {
      users: recommenderResult.recommendations.slice(0, limit),
      source: 'recommender_users',
    };
  }

  const users = await prisma.user.findMany({
    where: {
      AND: [
        { user_id: { not: userId } },
        {
          followers: {
            none: {
              follower_id: userId,
            },
          },
        },
      ],
    },
    select: {
      user_id: true,
      username: true,
      display_name: true,
      avatar_url: true,
      bio: true,
    },
    orderBy: {
      followers: {
        _count: 'desc',
      },
    },
    take: limit,
  });

  return {
    users,
    source: 'popular_users',
  };
};
