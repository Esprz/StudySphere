import prisma from '../utils/prisma';

export const createComment = async (
  post_id: string,
  user_id: string,
  content: string,
  parent_id?: string
) => {
  return await prisma.comment.create({
    data: {
      post_id,
      user_id,
      content,
      parent_id,
    },
  });
};

export const deleteComment = async (comment_id: string) => {
  return await prisma.comment.delete({ where: { comment_id } });
};

export const getCommentsByPost = async (post_id: string) => {
  return await prisma.comment.findMany({
    where: { post_id },
    orderBy: { created_at: 'asc' },
    include: {
      user: {
        select: {
          user_id: true,
          display_name: true,
          avatar_url: true,
        },
      },
    },
  });
};
