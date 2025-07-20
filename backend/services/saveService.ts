import prisma from '../utils/prisma';
import { eventService } from './eventService';

export const savePost = async (post_id: string, user_id: string) => {
  const existing = await prisma.save.findFirst({
    where: { post_id, user_id },
  });

  if (existing) return null;

  const newSave = await prisma.save.create({
    data: { post_id, user_id },
  });

  setImmediate(async () => {
    try {
      await eventService.trackPostSaved(post_id, user_id);
    } catch (error) {
      console.error('Event tracking failed:', error);
    }
  });
  return newSave;
};

export const deleteSave = async (save_id: string) => {
  return await prisma.save.delete({ where: { save_id } });
};

export const getSavedPosts = async (user_id: string) => {
  return await prisma.post.findMany({
    where: {
      saves: {
        some: { user_id },
      },
    },
    include: {
      user: {
        select: {
          display_name: true,
          avatar_url: true,
        },
      },      
      saves: {
        select: {
          save_id: true,
        },
      },
    },
    orderBy: { updated_at: 'desc' },
  });
};
