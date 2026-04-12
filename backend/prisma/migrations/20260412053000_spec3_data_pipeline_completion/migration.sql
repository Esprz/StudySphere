-- CreateEnum
CREATE TYPE "TaskStatus" AS ENUM ('PENDING', 'COMPLETED', 'ARCHIVED');

-- AlterTable
ALTER TABLE "FocusTime" ADD COLUMN     "sourceTrigger" TEXT,
ADD COLUMN     "tags" TEXT[] DEFAULT ARRAY[]::TEXT[],
ALTER COLUMN "end" DROP NOT NULL;

-- AlterTable
ALTER TABLE "Post" ADD COLUMN     "difficulty" INTEGER,
ADD COLUMN     "topicTags" TEXT[] DEFAULT ARRAY[]::TEXT[];

-- AlterTable
ALTER TABLE "User" ADD COLUMN     "goalTags" TEXT[] DEFAULT ARRAY[]::TEXT[],
ADD COLUMN     "habitLevel" DOUBLE PRECISION NOT NULL DEFAULT 0.5,
ADD COLUMN     "timezone" TEXT;

-- CreateTable
CREATE TABLE "Task" (
    "task_id" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "goal_id" TEXT,
    "status" "TaskStatus" NOT NULL DEFAULT 'PENDING',
    "due_at" TIMESTAMP(3),
    "completed_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Task_pkey" PRIMARY KEY ("task_id")
);

-- CreateIndex
CREATE INDEX "Task_user_id_status_idx" ON "Task"("user_id", "status");

-- CreateIndex
CREATE INDEX "Task_goal_id_idx" ON "Task"("goal_id");

-- AddForeignKey
ALTER TABLE "Task" ADD CONSTRAINT "Task_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("user_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Task" ADD CONSTRAINT "Task_goal_id_fkey" FOREIGN KEY ("goal_id") REFERENCES "Goal"("goal_id") ON DELETE SET NULL ON UPDATE CASCADE;

