import React, { useState } from "react";
import { Button } from "@/components/ui/button";

const mockUsers = [
    {
      id: "1",
      name: "Alice Johnson",
      avatar: "/assets/images/user1.jpg",
      bio: "Frontend Developer | React Enthusiast",
      isFollowing: false,
    },
    {
      id: "2",
      name: "Bob Smith",
      avatar: "/assets/images/user2.jpg",
      bio: "Backend Engineer | Node.js Expert",
      isFollowing: false,
    },
    {
      id: "3",
      name: "Charlie Brown",
      avatar: "/assets/images/user3.jpg",
      bio: "Fullstack Developer | Open Source Contributor",
      isFollowing: false,
    },
    {
      id: "4",
      name: "Diana Prince",
      avatar: "/assets/images/user4.jpg",
      bio: "Cloud Architect | AWS Certified",
      isFollowing: false,
    },
    {
      id: "5",
      name: "Eve Adams",
      avatar: "/assets/images/user5.jpg",
      bio: "UI/UX Designer | Figma Lover",
      isFollowing: false,
    },
    {
      id: "6",
      name: "Frank White",
      avatar: "/assets/images/user6.jpg",
      bio: "Data Scientist | Python Enthusiast",
      isFollowing: false,
    },
  ];

const UsersSuggested = () => {
  const [users, setUsers] = useState(mockUsers);

  const handleFollow = (id: string) => {
    setUsers((prevUsers) =>
      prevUsers.map((user) =>
        user.id === id ? { ...user, isFollowing: !user.isFollowing } : user
      )
    );
  };

  return (
    <div className="flex flex-col gap-4 p-4 ">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-bold text-primary-500">Suggested Users</h2>
        <p className="text-sm text-gray-500">
          Follow these users to expand your network!
        </p>
      </div>

      {/* User List */}
      <ul className="flex flex-col gap-4">
        {users.slice(0, 5).map((user) => (
          <li key={user.id} className="flex items-center gap-4">
            {/* Avatar */}
            <img
              src={user.avatar}
              alt={user.name}
              className="w-12 h-12 rounded-full"
            />

            {/* User Info */}
            <div className="flex-1">
              <p className="font-medium text-gray-800">{user.name}</p>
              <p className="text-sm text-gray-500">{user.bio}</p>
            </div>

            {/* Follow Button */}
            <Button
              variant={user.isFollowing ? "default" : "outline"}
              onClick={() => handleFollow(user.id)}
              className="px-4 py-2"
            >
              {user.isFollowing ? "Following" : "Follow"}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default UsersSuggested;