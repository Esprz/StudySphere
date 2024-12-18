import { deleteFile, uploadFile, getFilePreview } from '@/lib/appwrite/api';
import { PNewPost, PNewUser } from '@/types/postgresTypes';
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
        console.log('server:currentUser:', response);
        return response.data;
    } catch (error: any) {
        console.error("Token verification failed:", error.response?.data || error.message);
        throw error;
    }
};

/*-------------------Post API calls-------------------*/

export const createPost = async (newPost: PNewPost) => {
    try {

        // upload image
        const uploadedFile = await uploadFile(newPost.images[0]);
        if (!uploadedFile) throw Error;

        // image url
        const fileUrl = getFilePreview(uploadedFile.$id);
        if (!fileUrl) {
            deleteFile(uploadedFile.$id);
            throw Error;
        }

        const response = await API.post('/posts', {
            content: newPost.content,
            image: fileUrl,
            author: newPost.author,
        });
        return response.data;

    } catch (error: any) {
        console.error('Create post failed:', error.response?.data || error.message);
        throw error;
    }
}
export const updatePost = async (post_id: String, updatedPost: any) => {
    const hasFileToUpdate = updatedPost.images.length > 0;
    try {
        console.log('api:updatePost2')
        let fileUrl = updatedPost.image;
        if (hasFileToUpdate) {
            console.log('hasFileToUpdate:',hasFileToUpdate)

            // upload image
            const uploadedFile = await uploadFile(updatedPost.images[0]);
            if (!uploadedFile) throw Error;

            console.log('uploadedFile:',uploadedFile)

            // image url
            fileUrl = getFilePreview(uploadedFile.$id);
            if (!fileUrl) {
                deleteFile(uploadedFile.$id);
                throw Error;
            }
        }
        const response = await API.patch(`/posts/${post_id}`, {
            content: updatedPost.content,
            image: fileUrl,
            post_id: post_id,
        });
        console.log('Update post:', response.data);
        return response.data;
        
    } catch (error: any) {
        console.error('Update post failed:', error.response?.data || error.message);
        throw error;        
    }
};

export const deletePost = async (post_id: String) => {
    try {
        const response = await API.delete(`/posts/${post_id}`);
        console.log('Delete post:', response.data);
        return response.data;
    }
    catch (error: any) {
        console.error('Delete post failed:', error.response?.data || error.message);
        throw error;
    }
}
export const getAllPosts = () => API.get('/posts');

export const getRecentPosts = async () => {
    try {
        const response = await API.get('/posts/recent');
        console.log('Get recent posts:', response.data);
        return response.data;
    } catch (error: any) {
        console.error('Get recent posts failed:', error.response?.data || error.message);
        throw error;
    }
}

export const getPostById = async (post_id: String) => {
    try {
        const response = await API.get(`/posts/${post_id}`);
        console.log('Get post by id:', response.data);
        return response.data;
    } catch (error: any) {
        console.error('Get post by id failed:', error.response?.data || error.message);
        throw error;
    }
}

export const likePost = (post_id: Number) => API.post(`/posts/${post_id}/like`);
export const deleteLike = (post_id: Number, like_id: Number) => API.delete(`/posts/${post_id}/like/${like_id}`);

export const savePost = (post_id: Number) => API.post(`/posts/${post_id}/save`);
export const deleteSave = (post_id: Number, save_id: Number) => API.delete(`/posts/${post_id}/save/${save_id}`);


export const getLikedPosts = (user_id: Number) => API.get(`/posts/${user_id}/likes`);
export const getSavedPosts = (user_id: Number) => API.get(`/posts/${user_id}/saves`);

