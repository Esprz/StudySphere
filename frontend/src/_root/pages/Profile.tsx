import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import GoalsCard from "@/components/ui/shared/GoalsCard";
import Loader from "@/components/ui/shared/Loader";
import PostCard from "@/components/ui/shared/PostCard";
import { useToast } from "@/components/ui/use-toast";
import { useFollowUser, useGetFollowees, useGetPostByUser, useGetUserInfo, useUnfollowUser } from "@/lib/react-query/queriesAndMutations";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { set } from "zod";

const Profile = () => {
  const { username } = useParams();
  const {toast} = useToast();
  const navigate = useNavigate();
  if (!username){    
    toast({
      title: "Error",
      description: "No username found",
      duration: 3000,
    });
    navigate("/");
    return (<p className="text-light-2 font-normal self-auto text-lg">No username found</p>);
  }
  const { data: posts, isPending: isPostLoading, isError: isPostLoadingError } = useGetPostByUser(username);
  const { data: user, isPending: isUserLoading, isError: isUserLoadingError } = useGetUserInfo(username);
  const { data: follwees, isPending: isFolloweeLoading } = useGetFollowees();  
  console.log("follwees", follwees);

  const followUserMutation = useFollowUser();
  const unfollowUserMutation = useUnfollowUser();

  const [isFollowing, setIsFollowing] = useState(false);

  useEffect(() => {
    if (follwees) {
        setIsFollowing(follwees.find((followee: any) => followee.username === username));
    }
}, [follwees, username, isFolloweeLoading]);
  
  const studyTime = 47;
  const handleFollow = async (username: string) => {
    // Optimistically update local state
if (isFollowing){
      // Unfollow the user
      await unfollowUserMutation.mutateAsync(username);
      setIsFollowing(false);
    } else {
      // Follow the user
      await followUserMutation.mutateAsync(username);
      setIsFollowing(true);
    }
  };

  return (
    <div className="grid grid-cols-8 gap-4 w-full">
      {/* Main section */}
      {isUserLoading && !user
        ? (<Loader />)
        : (isUserLoadingError ? (
          <p className="text-light-2 font-normal text-lg">Error loading user</p>
        ) :
          (<div className="lg:col-span-3 full home-container col-span-8 ">
            {/* Header */}
            <div className="home-header px-8">
              <div className="flex flex-row gap-4 justify-between items-center">
                {/* Avatar */}
                <div className="flex items-stretch gap-8">
                  <img src={user.avatar_url || '/assets/icons/profile-placeholder.svg'}
                    alt='profile'
                    className='h-20 w-20 rounded-full' />

                  <div>
                    <h1 className="h2-bold md:h1-bold text-left w-full text-light-2">
                      {user.display_name}
                    </h1>
                    <p className="text-left w-full">
                      @{user.username}
                    </p>
                  </div>
                </div>
                {/* Follow Button */}
                <Button
                  variant={isFollowing ? "destructive" : "outline"}
                  onClick={() => handleFollow(user.username)}
                  className={"px-4 py-2 "+(isFollowing ? "bg-primary hover:bg-pr":"")}
                  disabled={followUserMutation.isPending || unfollowUserMutation.isPending || isFolloweeLoading}
                >
                  {isFollowing ? "Following" : "Follow"}
                </Button>
              </div>
              

            </div>
            {/* Profile*/}
            <div className="home-posts">
              <Card className="w-full flex flex-col mt-8 gap-4 px-8 border-none">
                <h3 className="h3-bold md:h2-bold text-left w-full ">
                  Bio
                </h3>
                <p className="text-left w-full">
                  {user.biol ? user.biol : "This user havent written bio"}
                </p>
              </Card>
              <Card className="w-full flex flex-col mt-8 gap-4 px-8  border-none">
                <h3 className="h3-bold md:h2-bold text-left w-full ">
                  Study Hours
                </h3>
                <h2>
                  {studyTime} hours
                </h2>
              </Card>
              <GoalsCard />
            </div>
          </div>))}
      {/* Sub Section Widget: My posts */}
      <div className="lg:col-span-5 lg:grid col-span-0 right-side-container w-full ">
        <div className="py-10 mt-4 gap-4 w-full flex justify-center">
          {/* Posts */}
          <div className="home-posts">
            <h2 className="h3-bold md:h2-bold w-full">
              {isPostLoading && !posts ? (
                <Loader />
              ) : (
                !posts || isPostLoadingError ? (
                  <p className="text-light-2 font-normal text-lg">Error loading posts</p>
                ) :
                  (posts.length === 0 ? (
                    <p className="text-light-2 font-normal text-lg">No posts found</p>
                  ) : (
                    <ul className="flex flex-col flex-1 gap-9 w-full">
                      {posts.map((post: any) => (

                        <PostCard key={post.post_id} post={post} />

                      ))}
                    </ul>)))}
            </h2>
          </div>
        </div>
      </div >
    </div>
  )

}

export default Profile
