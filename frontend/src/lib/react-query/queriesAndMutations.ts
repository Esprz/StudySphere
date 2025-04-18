import {
    useQuery,
    useMutation,
    useQueryClient,
    useInfiniteQuery,
} from '@tanstack/react-query'
import { getUsers,} from '../appwrite/api'
import { QUERY_KEYS } from './queryKey';
import { signIn, signUp, getCurrentUser,
    createPost,  getRecentPosts, updatePost, getPostById, getInfinitePosts,deletePost, 
    likePost, getLikedPosts, deleteLike,
    savePost,deleteSave,getSavedPosts,
    searchPosts,     
    getPostByUser,
    getUserInfo} from '@/api';
import { PNewPost, PNewUser, PUpdatedPost } from '@/types/postgresTypes';
import { useUserContext } from '@/context/AuthContext';


export const useCreateUSerAccount = () => {
    return useMutation({
        mutationFn: (user: PNewUser) => signUp(user)
    })
}

export const useSignInAccount = () => {
    return useMutation({
        mutationFn: (user: { email: string; password: string; }) => signIn(user)
    })
}

export const useSignOutAccount = () => {
    const { logout } = useUserContext();
    return useMutation({
        mutationFn: () => logout()
    })
}

export const useCreatePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (post: PNewPost) => createPost(post),
        // if successfully create post, 
        // invalidate the recent post, so that next time it wont able get posts from cache but need to request from server
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_RECENT_POSTS]
            })
        }
    });
};

export const useUpdatePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (post: PUpdatedPost) => updatePost(post.post_id, post),
        onSuccess: (data) => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_POST_BY_ID, data?.$id]
            })
        }
    })
}

export const useGetRecentPosts = () => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_RECENT_POSTS],
        queryFn: getRecentPosts,
    })
}

/*
export const useLikePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ postId }: { postId: string }) => likePost(postId),
        onSuccess: (data) => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_POST_BY_ID, data?.$id]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_RECENT_POSTS]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_POSTS]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_CURRENT_USER]
            })
        }
    })
}
*/

export const useGetLikes = () => {
    return useQuery({
        queryKey: [QUERY_KEYS.LIKE_LIST],
        queryFn: () => getLikedPosts(),
    });
};

export const useLikePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (postId: string) => likePost(postId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.LIKE_LIST], 
            });
        }
    })
}

export const useDeleteLike = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (likeId: string) => deleteLike(likeId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.LIKE_LIST], 
            });
        }
    })
}

export const useSavePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ( postId: string) => savePost(postId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_RECENT_POSTS]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_POSTS]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_CURRENT_USER]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.SAVED_POSTS], 
            });
        }
    })

}

export const useDeleteSavedPost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (savedId: string) => deleteSave(savedId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_RECENT_POSTS]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_POSTS]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_CURRENT_USER]
            })
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.SAVED_POSTS], 
            });
        }
    })

}

export const useGetSavedPosts = () => {
    return useQuery({
        queryKey: [QUERY_KEYS.SAVED_POSTS],
        queryFn: getSavedPosts,
    });
};

export const useGetCurrentUser = () => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_CURRENT_USER],
        queryFn: getCurrentUser,
    })
}

export const useGetUserInfo = (username: string) => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_USER_INFO, username],
        queryFn: () => getUserInfo(username),
        enabled: !!username,  // cache data more efficiently, avoid refetching for the same postId
    })
}

export const useGetPostById = (postId: string) => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_POST_BY_ID, postId],
        queryFn: () => getPostById(postId),
        enabled: !!postId,  // cache data more efficiently, avoid refetching for the same postId
    })
}

export const useGetPostByUser = (username: string) => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_POST_BY_USER, username],
        queryFn: () => getPostByUser(username),
        enabled: !!username,  // cache data more efficiently, avoid refetching for the same postId
    })
}


export const useDeletePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ postId, image }: { postId: string, image: object }) => deletePost(postId, image),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: [QUERY_KEYS.GET_RECENT_POSTS]
            })
        }
    })
}


export const useGetPosts = () => {
    return useInfiniteQuery({
        queryKey: [QUERY_KEYS.GET_INFINITE_POSTS],
        queryFn: ({ pageParam = 0 }) => getInfinitePosts({ page: pageParam }),
        initialPageParam: 0,
        getNextPageParam: (lastPage) => {
            if (lastPage && lastPage.length === 0) return null;
            const lastId = lastPage?.[lastPage.length - 1].$id;
            return lastId;
        },
    })

}

export const useSearchPosts = (searchTerm: string) => {
    return useQuery({
        queryKey: [QUERY_KEYS.SEARCH_POSTS, searchTerm],
        queryFn: () => searchPosts(searchTerm),
        enabled: !!searchTerm
    })
}

export const useGetUsers = () => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_USERS],
        queryFn: getUsers
    })
}