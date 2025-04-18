import { Button } from '@/components/ui/button';
import Loader from '@/components/ui/shared/Loader';
import PostStats from '@/components/ui/shared/PostStats';
import { toast } from '@/components/ui/use-toast';
import { useUserContext } from '@/context/AuthContext';
import { useDeletePost, useGetPostById } from '@/lib/react-query/queriesAndMutations'
import { formatTime } from '@/lib/utils';
import { Link, useNavigate, useParams } from 'react-router-dom';

const PostDetails = () => {
  const { id } = useParams();
  const { data: post, isPending } = useGetPostById(id || '');
  const { user } = useUserContext();
  const { mutate: deletePost, isPending: isDeletingPost } = useDeletePost();
  const navigator = useNavigate();

  const handleDeletePost = () => {
    if (!post) return;

    const confirmDelete = window.confirm('Are you sure you want to delete this post?');
    if (!confirmDelete) return;

    deletePost({ postId: post.post_id, image: post.image }, {
      onSuccess: () => {
        console.log('post deleted');
        toast({
          title: 'Post deleted',
          description: 'Your post has been deleted successfully.',
          variant: 'default',
        });
        navigator('/'); // Redirect to home page after deletion
      },
      onError: (error) => {
        console.error('Error deleting post:', error);
        toast({
          title: 'Error deleting post',
          description: 'There was an error deleting your post. Please try again later.',
          variant: 'destructive',
        });
      }
    });

  };
  if (post) console.log('post!!!11', post);

  return (
    <div className='post_details-container'>
      {isPending || isDeletingPost
        ? <Loader />
        : <div className='post_details-card'>
          <img src={post?.image.fileUrl} alt='post' className='post_details-img' />
          <div className='post_details-info'>
            <div className='flex-between w-full'>
              <Link to={`/profile/${post?.user.username}`} className='flex items-center gap-3'>
                <img src={post?.user.avatar_url || '/assets/icons/profile-placeholder.svg'}
                  alt='creator'
                  className='rounded-full w-8 h-8 lg:w-12 lg:h-12' />

                <div className='flex flex-col'>
                  <p className='base-medium lg:body-bold text-light-1'>
                    {post?.user.display_name}
                  </p>
                  <div className='flex-center gap-2 text-light-3'>
                    <p className='subtle-semibold lg:small-regular'>
                      {formatTime(post?.updated_at || '')}
                    </p>
                  </div>
                </div>
              </Link>
              <div className='flex-center gap-1'>

                <Link to={`/update-post/${post?.post_id}`} className={`${user.username !== post?.user.username && 'hidden'}`}>
                  <img src='/assets/icons/edit.svg' alt='edit' width={24} height={24} />
                </Link>

                <Button onClick={handleDeletePost} variant="ghost" className={`ghost_details-delete_btn ${user.username !== post?.user.username && 'hidden'}`}>
                  <img src='/assets/icons/delete.svg' alt='delete' width={24} height={24} />
                </Button>

              </div>
            </div>
            <hr className='border w-full border-dark-4/80' />

            <div className='flex flex-col flex-1 w-full '>
              <h3 className='text-xl font-medium mb-4'>{post?.title}</h3>
              <p className='text-light-1 small-medium lg:base-regular'>{post?.content}</p>

            </div>

            <div className='w-full'>
              <PostStats post={post} />
            </div>

          </div>
        </div>}
    </div>
  )
}

export default PostDetails
