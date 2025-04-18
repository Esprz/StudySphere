import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useFollowUser, useGetSuggestedToFollow, useUnfollowUser } from "@/lib/react-query/queriesAndMutations";
import Loader from "./Loader";
import { Link } from "react-router-dom";



const UsersSuggested = () => {

  const { data: suggestedUsers, isPending: isUsersLoading, isError } = useGetSuggestedToFollow();
  const [users, setUsers] = useState(suggestedUsers);

  useEffect(() => {
    if (!isUsersLoading && !isError && suggestedUsers) {
      setUsers(suggestedUsers.map((user) => ({ ...user, isFollowing: false })));
    }
  }, [suggestedUsers, isUsersLoading, isError]);

  const followUserMutation = useFollowUser();
  const unfollowUserMutation = useUnfollowUser();

  if (suggestedUsers){
    console.log("suggestedUsers:", suggestedUsers);
  }

  const handleFollow = async (username: string, isFollowing: boolean) => {
    // Optimistically update local state
    setUsers((prevUsers) =>
      prevUsers.map((user) =>
        user.username === username ? { ...user, isFollowing: !isFollowing } : user
      )
    );

    try {
      if (isFollowing) {
        // Unfollow the user
        await unfollowUserMutation.mutateAsync(username);
      } else {
        // Follow the user
        await followUserMutation.mutateAsync(username);
      }
    } catch (error) {
      console.error("Error updating follow status:", error);

      // Rollback local state if API call fails
      setUsers((prevUsers) =>
        prevUsers.map((user) =>
          user.username === username ? { ...user, isFollowing: isFollowing } : user
        )
      );
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4 ">
      {
        isUsersLoading || isError || !users || !suggestedUsers ? (
          isUsersLoading ? (
            <Loader />
          ) : (
            <p>Error loading suggested users.</p>
          )) : (
          users.length === 0 ? (
            <p className="text-light-2 font-normal text-lg">No suggested users found</p>
          ) : (
            <>
              {/* Header */}
              <div className="mb-4">
                <h2 className="text-lg font-bold text-primary-500">Suggested Users</h2>
                <p className="text-sm text-gray-500">
                  Follow these users to expand your network!
                </p>
              </div>

              {/* User List */}
              <ul className="flex flex-col gap-4">
                {users.map((user) => (                  
                  <li key={user.username} className="flex items-center gap-4">
                    {/* Avatar */}
                    <Link to={`/profile/${user.username}`}>
                    <img
                      src={user.avatar_url || "/assets/icons/profile-placeholder.svg"}
                      alt={user.display_name}
                      className="w-12 h-12 rounded-full"
                    />
                    </Link>

                    {/* User Info */}
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">{user.display_name}</p>
                      <p className="text-sm text-gray-500">{user.bio}</p>
                    </div>

                    {/* Follow Button */}
                    <Button
                      variant={user.isFollowing ? "destructive" : "outline"}
                      onClick={() => handleFollow(user.username, user.isFollowing)}
                      className={"px-4 py-2 "+(user.isFollowing ? "bg-primary hover:bg-pr":"")}
                      disabled={followUserMutation.isPending || unfollowUserMutation.isPending}
                    >
                      {user.isFollowing ? "Following" : "Follow"}
                    </Button>
                  </li>
                ))}
              </ul>
            </>
          ))
      }
    </div>
  );
};

export default UsersSuggested;