import { useUserContext } from '@/context/AuthContext'
import { Models } from 'appwrite'
import React, { useContext } from 'react'
import { Link } from 'react-router-dom'
import PostStats from './PostStats'
import { PPost } from '@/types/postgresTypes'

type GridPostListProps = {
    posts: any[],
    showUser?: boolean,
    showStat?: boolean
}

const GridPostList = ({ posts, showUser = true, showStat = true }: GridPostListProps) => {
    const { user } = useUserContext();
    return (
        <ul className='grid-container'>
            {posts.map((post) => (
                <li key={post.post_id} className='relative min-w-80 h-80'>
                    <Link to={`/post/${post.post_id}`} className='grid-post_link'>
                        <img src={post.image.fileUrl} className='h-full w-full object-cover' />
                    </Link>

                    <div className='grid-post_user'>
                        {showUser && (
                            <div className='flex items-center justify-start gap-2 flex-1'>
                                <img src={post.author_avatar || '/assets/icons/profile-placeholder.svg'} alt="creator" className='h-8 w-8 rounded-full' />
                                <p className='line-clamp-1'> {post.user.display_name}</p>
                            </div>
                        )}
                        {showStat && <PostStats post={post} />}

                    </div>
                </li>
            ))}

        </ul>
    )
}

export default GridPostList
