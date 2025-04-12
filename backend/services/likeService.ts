import prisma from '../utils/prisma';

export const likePost = async (post_id: string, user_id: string) => {
  // Optional: check if already liked
  const existing = await prisma.like.findFirst({
    where: { post_id, user_id },
  });

  if (existing) return null;

  return await prisma.like.create({
    data: { post_id, user_id },
  });
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
