import { useUserContext } from '@/context/AuthContext';
import { formatTime } from '@/lib/utils';
import { Models } from 'appwrite'
import { Link } from 'react-router-dom';
import PostStats from './PostStats';
import { PPost } from '@/types/postgresTypes';

type PostCardProps = {
    post: PPost;
}

const PostCard = ({ post }: PostCardProps) => {
    const { user } = useUserContext();
    if (!post.author) return;
    console.log("user_id:",user.user_id);

    return (
        <div className='post-card'>
            
            <div className='flex-between'>
                
                <div className='flex items-center gap-3'>
                    <Link to={`/profile/${post.author}`}>
                        <img src= {post.author_avatar || '/assets/icons/profile-placeholder.svg'}
                            alt='creator'
                            className='rounded-full w-12 lg:h-12' />
                    </Link>
                    <div className='flex flex-col'>
                        <p className='base-medium lg:body-bold text-light-1'>{post.author_name}</p>
                        <div className='flex-center gap-2 text-light-4'>
                            <p className='small-regular'>{formatTime(post.updated_at)}</p>
                        </div>
                    </div>

                </div>
                <Link to={`/update-post/${post.post_id}`} className={`${user.user_id !== post.author && "hidden"}`}>
                    <img src='/assets/icons/edit.svg' alt='edit' width={20} />
                </Link>
            </div>
                
            <Link to={`/post/${post.post_id}`}>
                <div className='small-medium lg:base-medium py-5 text-light-2'>
                    <p>{post.content}</p>
                </div>
                <img src={post.image || '/assets/icons/profile-placeholder.svg'}
                    className='post-card_img'
                    alt='post image' />

            </Link>
            {/* 
            <PostStats post={post} userId={user.user_id} />*/}
        </div>
    )
}

export default PostCard
