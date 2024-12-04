import { INewUser } from '@/types';
import axios from 'axios';

const url = 'http://localhost:5000';
const API = axios.create({ baseURL: url });

/*-------------------Auth API calls-------------------*/
export const signIn = async (user:any) => {
    try {
        const response = await API.post('/auth/sign-in', {
            email: user.email,
            password: user.password,
        });
        return response.data;
    } catch (error: any) {
        console.error('Sign-in failed:', error.response?.data || error.message);
        throw error;
    }
};

export const signUp = async (user: INewUser) => {
    try {
        const response = await API.post('/auth/sign-up', {
            email: user.email,
            password: user.password,
            display_name: user.name,
            username: user.username,
        });
        return response.data;
    } catch (error: any) {
        console.error('Sign-up failed:', error.response?.data || error.message);
        throw error;
    }
};

/*-------------------Post API calls-------------------*/

export const createPost = (newPost: any) => API.post('/posts', newPost);
export const updatePost = (post_id: Number, updatedPost: any) => API.patch(`/posts/${post_id}`, updatedPost);
export const deletePost = (post_id: Number) => API.delete(`/posts/${post_id}`);
export const getAllPosts = () => API.get('/posts');
export const getPostById = (post_id: Number) => API.get(`/posts/${post_id}`);

export const likePost = (post_id: Number) => API.post(`/posts/${post_id}/like`);
export const deleteLike = (post_id: Number, like_id: Number) => API.delete(`/posts/${post_id}/like/${like_id}`);

export const savePost = (post_id: Number) => API.post(`/posts/${post_id}/save`);
export const deleteSave = (post_id: Number, save_id: Number) => API.delete(`/posts/${post_id}/save/${save_id}`);


export const getLikedPosts = (user_id: Number) => API.get(`/posts/${user_id}/likes`);
export const getSavedPosts = (user_id: Number) => API.get(`/posts/${user_id}/saves`);


