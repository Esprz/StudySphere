import GridPostList from "@/components/ui/shared/GridPostList";
import Loader from "@/components/ui/shared/Loader";
import { useGetCurrentUser } from "@/lib/react-query/queriesAndMutations";
import { Models } from "appwrite";


const Saved = () => {
  const { data: currentUser, isLoading: isLoadingSavedPosts } = useGetCurrentUser();

  if (isLoadingSavedPosts) {
    return <Loader />
  }

  const savedPosts = currentUser?.save.map((savedPost: Models.Document) => ({
    ...savedPost.post,
    creator: {
      imageUrl: currentUser.imageUrl,
    }
  }));
  console.log(currentUser);
  console.log(savedPosts);

  return (
    <div className="saved-container">
      {savedPosts.length === 0
        ? <p className='text-light-4 mt-10 text-center w-full'>No saved posts yet.</p>
        : <GridPostList posts={savedPosts} showStat={false} />}
    </div>
  )
}

export default Saved
