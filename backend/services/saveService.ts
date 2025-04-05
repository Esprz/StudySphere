import prisma from '../utils/prisma';

export const savePost = async (post_id: string, user_id: string) => {
  const existing = await prisma.save.findFirst({
    where: { post_id, user_id },
  });

  if (existing) return null;

  return await prisma.save.create({
    data: { post_id, user_id },
  });
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
    },
    orderBy: { updated_at: 'desc' },
  });
};
