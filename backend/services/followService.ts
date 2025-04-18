import prisma from '../utils/prisma';

export const createFollow = async (followee_username: string, follower_id: string) => {
  try {
    const existing = await prisma.follow.findFirst({
      where: {
        followee: {
          username: followee_username,
        },
        follower_id
      },
    });
    if (existing) return null;

    return await prisma.follow.create({
      data: {
        followee: {
          connect: { username: followee_username }, // Connect to the followee by username
        },
        follower: {
          connect: { user_id: follower_id }, // Connect to the follower by user_id
        },
      },
    });

  } catch (error) {
    console.error('Error creating follow:', error);
    throw new Error('Failed to create follow');
  }
};

export const deleteFollow = async (followee_username: string, follower_id: string) => {
  try {
    return await prisma.follow.deleteMany({
      where: {
        followee: {
          username: followee_username
        },
        follower_id: follower_id
      }
    });
  } catch (error) {
    console.error('Error deleting follow:', error);
    throw new Error('Failed to delete follow');
  }

};

export const getFollowers = async (user_id: string) => {
  try {
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
  } catch (error) {
    console.error('Error fetching followers:', error);
    throw new Error('Failed to fetch followers');
  }
};


export const getFollowees = async (user_id: string) => {
  try {
    return await prisma.follow.findMany({
      where: { follower_id: user_id },
      include: {
        followee: {
          select: {
            user_id: true,
            username: true,
            display_name: true,
            avatar_url: true,
          },
        },
      },
    });
  } catch (error) {
    console.error('Error fetching followees:', error);
    throw new Error('Failed to fetch followees');
  }
};

export const getSuggestedToFollow = async (user_id: string) => {
  try {
    return await prisma.user.findMany({
      where: {
        AND: [
          { user_id: { not: user_id } }, // Exclude the current user
          {
            followers: {
              none: {
                follower_id: user_id, // Exclude users already followed by the current user
              },
            },
          },
        ],
      },
      select: {
        username: true,
        display_name: true,
        avatar_url: true,
        bio: true,
      },
      take: 5,
    });
  } catch (error) {
    console.error('Error fetching suggested users to follow:', error);
    throw new Error('Failed to fetch suggested users to follow');
  }
}

