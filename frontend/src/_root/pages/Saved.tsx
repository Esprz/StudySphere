import GridPostList from "@/components/ui/shared/GridPostList";
import Loader from "@/components/ui/shared/Loader";
import { useGetSavedPosts } from "@/lib/react-query/queriesAndMutations";

const Saved = () => {
  const { data: savedPosts, isLoading: isLoadingSavedPosts } = useGetSavedPosts();

  if (isLoadingSavedPosts) {
    return <Loader />;
  }

  if (!savedPosts || savedPosts.length === 0) {
    return (
      <div className="saved-container">
        <p className="text-light-4 mt-10 text-center w-full">No saved posts yet.</p>
      </div>
    );
  }

  return (
    <div className="saved-container">
      {savedPosts.length === 0
        ? <p className='text-light-4 mt-10 text-center w-full'>No saved posts yet.</p>
        : <GridPostList posts={savedPosts} showStat={false} />}
    </div>
  )
}

export default Saved
