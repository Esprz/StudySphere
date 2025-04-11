import React, { useEffect, useState } from 'react';
import { useGetSavedPosts, useSavePost, useDeleteSavedPost, useLikePost, useDeleteLike } from '@/lib/react-query/queriesAndMutations';
import { useGetLikes,  } from '@/lib/react-query/queriesAndMutations';
import Loader from './Loader';
import { PPost } from '@/types/postgresTypes';

type PostStatsProps = {
    post: PPost;
};

const PostStats = ({ post }: PostStatsProps) => {
    const { data: savedPosts = [], isLoading: isSavedPostsLoading } = useGetSavedPosts();
    const { data: likeList = [], isLoading: isLikesLoading } = useGetLikes();

    const { mutate: savePost, isPending: isSavingPost } = useSavePost();
    const { mutate: deleteSavedPost, isPending: isDeletingSaved } = useDeleteSavedPost();

    const { mutate: deleteLike, isPending: isDeletingLike } = useDeleteLike();
    const { mutate: likePost, isPending: isLikingPost } = useLikePost();


    // Handle like/unlike
    const handleLikePost = (e: React.MouseEvent) => {
        e.stopPropagation();
        //const hasLiked = likeList.includes(userId);
        const likeRecord = likeList.find((likedPost: any) => likedPost.post_id === post.post_id);
        if (likeRecord) {
            deleteLike( likeRecord.likes[0].like_id );
        }
        else {
            likePost(post.post_id);
        }
    };

    // Handle save/unsave
    const handleSavedPost = (e: React.MouseEvent) => {
        e.stopPropagation();
        const savedRecord = savedPosts.find((savedPost: any) => savedPost.post_id === post.post_id);
        if (savedRecord) {
            deleteSavedPost(savedRecord.saves[0].save_id);
        }
         else {
            savePost( post.post_id );
        }
    };

    return (
        <div className="flex justify-between items-center z-20">
            {/* Like Section */}
            <div className="flex gap-2 mr-5">
                {isLikesLoading ? (
                    <Loader />
                ) : (
                    <>
                        <img
                            src={likeList.find((likedPost: any) => likedPost.post_id === post.post_id)
                                ? '/assets/icons/liked.svg'
                                : '/assets/icons/like.svg'}
                            alt="like"
                            width={20}
                            height={20}
                            onClick={handleLikePost}
                            className="cursor-pointer"
                        />
                        <p className="small-medium lg:base-medium text-light-4">{likeList.length}</p>
                    </>
                )}
            </div>

            {/* Save Section */}
            <div className="flex gap-2">
                {isSavingPost || isDeletingSaved || isSavedPostsLoading ? (
                    <Loader />
                ) : (
                    <img
                        src={savedPosts.find((savedPost: any) => savedPost.post_id === post.post_id) ? '/assets/icons/saved.svg' : '/assets/icons/save.svg'}
                        alt="save"
                        width={20}
                        height={20}
                        onClick={handleSavedPost}
                        className="cursor-pointer"
                    />
                )}
            </div>
        </div>
    );
};

export default PostStats;