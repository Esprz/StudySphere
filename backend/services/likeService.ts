import prisma from '../utils/prisma';
import { eventService } from './eventService';

export const likePost = async (post_id: string, user_id: string) => {
  // Mandatory: check if already liked to prevent duplicate likes
  const existing = await prisma.like.findFirst({
    where: { post_id, user_id },
  });

  if (existing) return null;

  const newLike = await prisma.like.create({
    data: { post_id, user_id },
  });

  setImmediate(async () => {
    try {
      await eventService.trackPostLiked(post_id, user_id);
    } catch (error) {
      console.error('Event tracking failed:', error);
    }
  });

  return newLike;
};

export const deleteLike = async (like_id: string) => {
  return await prisma.like.delete({ where: { like_id } });
};

export const getLikedPosts = async (user_id: string) => {
  return await prisma.post.findMany({
    where: {
      likes: {
        some: { user_id },
      },
    },
    include: {
      user: {
        select: {
          display_name: true,
          username: true,
          avatar_url: true,
        },
      },
      likes: {
        select: {
          like_id: true,
        },
      },
    },
    orderBy: { updated_at: 'desc' },
  });
};
