import prisma from '../utils/prisma';

export const createFollow = async (followee_id: string, follower_id: string) => {
  const existing = await prisma.follow.findFirst({
    where: { followee_id, follower_id },
  });
  if (existing) return null;

  return await prisma.follow.create({
    data: { followee_id, follower_id },
  });
};

export const deleteFollow = async (follow_id: string) => {
  return await prisma.follow.delete({ where: { follow_id } });
};

export const getFollowers = async (user_id: string) => {
  return await prisma.follow.findMany({
    where: { followee_id: user_id },
    include: {
      follower: {
        select: {
          user_id: true,
          display_name: true,
          username: true,
          avatar_url: true,
        },
      },
    },
  });
};


export const getFollowees = async (user_id: string) => {
  return await prisma.follow.findMany({
    where: { follower_id: user_id },
    include: {
      follower: {
        select: {
          user_id: true,
          username: true,
          display_name: true,
          avatar_url: true,
        },
      },
    },
  });
};