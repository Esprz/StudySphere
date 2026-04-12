import prisma from '../utils/prisma';

interface StartFocusInput {
  user_id: string;
  goal_id?: string;
  start?: Date;
  tags?: string[];
  sourceTrigger?: string;
}

interface EndFocusInput {
  ft_id: string;
  user_id: string;
  end?: Date;
}

export const startFocus = async ({
  user_id,
  goal_id,
  start,
  tags,
  sourceTrigger,
}: StartFocusInput) => {
  return await prisma.focusTime.create({
    data: {
      user_id,
      goal_id,
      start: start ?? new Date(),
      tags: tags ?? [],
      sourceTrigger,
    },
  });
};

export const endFocus = async ({ ft_id, user_id, end }: EndFocusInput) => {
  return await prisma.focusTime.updateMany({
    where: {
      ft_id,
      user_id,
    },
    data: {
      end: end ?? new Date(),
    },
  });
};

export const getFocusSessions = async (user_id: string) => {
  return await prisma.focusTime.findMany({
    where: { user_id },
    orderBy: { start: 'desc' },
  });
};
