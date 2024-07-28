import {
    useQuery,
    useMutation,
    useQueryClient,
    useInfiniteQuery,
} from '@tanstack/react-query'
import { createPost, createUserAccount, getRecentPosts, signInAccount, signOutAccount } from '../appwrite/api'
import { INewPost, INewUser, IUpdatePost, IUpdateUser } from "@/types";
import { QUERY_KEYS } from './queryKey';


export const useCreateUSerAccount = () => {
    return useMutation({
        mutationFn: (user: INewUser) => createUserAccount(user)
    })
}

export const useSignInAccount = () => {
    return useMutation({
        mutationFn: (user: {email:string; password:string;}) => signInAccount(user)
    })
}

export const useSignOutAccount = () => {
    return useMutation({
        mutationFn: () => signOutAccount()
    })
}

export const useCreatePost = () => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (post: INewPost) => createPost(post),
      // if successfully create post, 
      // invalidate the recent post, so that next time it wont able get posts from cache but need to request from server
      onSuccess: ()=>{
        queryClient.invalidateQueries({
            queryKey: [QUERY_KEYS.GET_RECENT_POSTS]
        })
      }
    });
  };

  export const useGetRecentPosts = () => {
    return useQuery({
        queryKey: [QUERY_KEYS.GET_RECENT_POSTS],
        queryFn: getRecentPosts,
    })
  }