import Timer from "@/components/ui/shared/Timer";
import Loader from "@/components/ui/shared/Loader";
import PostCard from "@/components/ui/shared/PostCard";
import { useGetRecentPosts } from "@/lib/react-query/queriesAndMutations";
import GoalsCard from "@/components/ui/shared/GoalsCard";


const Home = () => {
  const { data: posts, isPending: isPostLoading } = useGetRecentPosts();
  return (
    <div className="grid grid-cols-8 gap-4 w-full">
      {/* Feed */}
      <div className="lg:col-span-5 full home-container col-span-8 ">
        {/* Header */}
        <div className="home-header">
          <h1 className="h2-bold md:h1-bold text-left w-full">
            Feeds
          </h1>
          <p className="text-light-2">Have you studied today?</p>
          <p className="text-light-2">See who's hitting the books!</p>
        </div>
        {/* Posts */}        
        <div className="home-posts">
          <h2 className="h3-bold md:h2-bold text-left w-full">        
            {isPostLoading && !posts? (
              <Loader />
            ) : (
              posts?.length === 0 ? (
                <p className="text-light-2 font-normal text-lg">No posts found</p>
              ) : (
              <ul className="flex flex-col flex-1 gap-9 w-full">
                {posts?.map((post: any) => (                  
                  <PostCard key={post.post_id} post={post} />                  
                ))}
              </ul>))}
          </h2>
        </div>
      </div>
      {/* Focus Widget */}
      <div className="lg:col-span-3 lg:grid col-span-0 right-side-container">
        <div className="py-10 mt-4 gap-4">
          <Timer />
          <GoalsCard />          
        </div>
        
      </div >
      
      
    </div>
  )
}

export default Home
