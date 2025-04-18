import Loader from "@/components/ui/shared/Loader";
import PostCard from "@/components/ui/shared/PostCard";
import { useGetFolloweeePosts, useGetRecentPosts } from "@/lib/react-query/queriesAndMutations";
import UsersSuggested from "@/components/ui/shared/UsersSuggested";

const Friends = () => {
  const { data: posts, isPending: isPostLoading, isError } = useGetFolloweeePosts();
  return (
    <div className="grid grid-cols-8 gap-4 w-full">
      {/* Main */}
      <div className="lg:col-span-5 full home-container col-span-8 ">
        {/* Header */}
        <div className="home-header">
          <h1 className="h2-bold md:h1-bold text-left w-full text-light-2">
            Friends Moments
          </h1>
          <p className="text-light-2">Have you studied today?</p>
          <p className="text-light-2">Your friends have studied 54 hours this week!</p>
        </div>
        {/* Posts */}
        <div className="home-posts">
          <h2 className="h3-bold md:h2-bold text-left w-full">
            {isPostLoading && !posts ? (
              <Loader />
            ) : (
              !posts || isError ? (
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
      {/* Subsection */}
      <div className="lg:col-span-3 lg:grid col-span-0 right-side-container ">
        <div className="py-10 px-8 mt-4 gap-4">
          <UsersSuggested />
        </div>

      </div >


    </div>
  )
}

export default Friends
