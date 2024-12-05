import { PNewUser } from '@/types/postgresTypes';
import axios from 'axios';

const url = 'http://localhost:5000';
const API = axios.create({ baseURL: url });
API.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers.Authorization = token;
    }
    return config;
});

/*-------------------Auth API calls-------------------*/
export const signIn = async (user: any) => {
    try {
        const response = await API.post('/auth/sign-in', {
            email: user.email,
            password: user.password,
        });
        localStorage.setItem("token", response.data.token);
        return response.data;
    } catch (error: any) {
        console.error('Sign-in failed:', error.response?.data || error.message);
        throw error;
    }
};

export const signUp = async (user: PNewUser) => {
    try {
        const response = await API.post('/auth/sign-up', {
            email: user.email,
            password: user.password,
            display_name: user.name,
            username: user.name,
        });
        localStorage.setItem("token", response.data.token);
        return response.data;
    } catch (error: any) {
        console.error('Sign-up failed:', error.response?.data || error.message);
        throw error;
    }
};

export const getCurrentUser = async () => {
    try {
        const response = await API.get("/auth/user");
        return response.data;
    } catch (error: any) {
        console.error("Token verification failed:", error.response?.data || error.message);
        throw error;
    }
};

/*-------------------Post API calls-------------------*/

export const createPost = async (newPost: any) => {
    try {
        const response = await API.post('/posts', {
            title: newPost.title,
            content: newPost.caption,
            images: newPost.file,
            author: newPost.userId,
        });
        return response.data;
    } catch (error: any) {
        console.error('Create post failed:', error.response?.data || error.message);
        throw error;
    }
}
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


