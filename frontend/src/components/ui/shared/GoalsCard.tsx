import { useState, useEffect } from 'react';
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";


const GoalsCard = () => {
    const [goals, setGoals] = useState([
        { id: 1, title: "Complete a 6-month coding bootcamp", completed: false },
        { id: 2, title: "Read 12 books this year", completed: false },
        { id: 3, title: "Build a personal portfolio website", completed: false },
        { id: 4, title: "Contribute to an open-source project", completed: false },
        { id: 5, title: "Achieve a certification in cloud computing", completed: false },
        { id: 6, title: "Learn a new programming language", completed: false },
      ]);
      // Toggle goal completion
      const toggleGoalCompletion = (id: number) => {
        setGoals((prevGoals) =>
          prevGoals.map((goal) =>
            goal.id === id ? { ...goal, completed: !goal.completed } : goal
          )
        );
      };

  return (
    <Card className="w-full flex flex-col mt-8 gap-4 p-8 border-none">
            <h3 className="h3-bold md:h2-bold text-left w-full ">My Goals</h3>
            {goals.length === 0 ? (
              <p className="text-light-2 font-normal text-lg">No goals set yet</p>
            ) : (
              <ol className="flex flex-col flex-1 gap-4 w-full">
                {goals.map((goal:any) => (
                  <li key={goal.id} className="flex items-center gap-4">
                    {/* Checkbox 
                    <Checkbox
                      checked={goal.completed}
                      onCheckedChange={() => toggleGoalCompletion(goal.id)}
                    />
                    */}
                    {/* Goal Title */}
                    <label
                      className={`text-light-2 font-normal text-md ${
                        goal.completed ? "line-through text-gray-400" : ""
                      }`}
                    >
                      {goal.id}. {goal.title}
                    </label>
                  </li>
                ))}
              </ol>
            )}
          </Card>
  );
};

export default GoalsCard;