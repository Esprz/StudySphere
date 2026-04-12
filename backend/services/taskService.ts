import prisma from '../utils/prisma';

interface CreateTaskInput {
  user_id: string;
  content: string;
  goal_id?: string;
  due_at?: Date;
}

export const createTask = async ({
  user_id,
  content,
  goal_id,
  due_at,
}: CreateTaskInput) => {
  return await prisma.task.create({
    data: {
      user_id,
      content,
      goal_id,
      due_at,
    },
  });
};

export const completeTask = async (task_id: string, user_id: string) => {
  return await prisma.task.updateMany({
    where: {
      task_id,
      user_id,
    },
    data: {
      status: 'COMPLETED',
      completed_at: new Date(),
    },
  });
};

export const getTasks = async (user_id: string) => {
  return await prisma.task.findMany({
    where: { user_id },
    orderBy: { created_at: 'desc' },
  });
};
