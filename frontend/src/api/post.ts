import { deleteFile, uploadFile, getFilePreview } from '@/lib/appwrite/api';
import { PNewPost } from '@/types/postgresTypes';
import { API } from './config';

export const createPost = async (newPost: PNewPost) => {
    try {
        // upload image
        const uploadedFile = await uploadFile(newPost.images[0]);
        /*let imageUrls = [];
        
        const uploadedFiles = await Promise.all(
            newPost.images.map(async (image) => {
                const uploadedFile = await uploadFile(image);
                if (!uploadedFile) throw new Error('Image upload failed');
                const fileUrl = getFilePreview(uploadedFile.$id);
                if (!fileUrl) {
                    await deleteFile(uploadedFile.$id);
                    throw new Error('Failed to generate file preview');
                }
                imageUrls.push(fileUrl);
                return fileUrl;
            })
        );*/
        if (!uploadedFile) throw Error;

        // image url
        const fileUrl = getFilePreview(uploadedFile.$id);
        if (!fileUrl) {
            deleteFile(uploadedFile.$id);
            throw Error;
        }
        const response = await API.post(`post`, {
            title: 'no title',            
            content: newPost.content,
            image: {fileUrl},
            extra: {},
            user_id: newPost.author,
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
        const response = await API.patch(`post/${post_id}`, {
            title: updatedPost.title,
            content: updatedPost.content,
            image: fileUrl,
            extra: updatedPost.extra || {},
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
        const response = await API.delete(`post/${post_id}`);
        console.log('Delete post:', response.data);
        return response.data;
    }
    catch (error: any) {
        console.error('Delete post failed:', error.response?.data || error.message);
        throw error;
    }
}
export const getAllPosts = async () => {
    try {
        const response = await API.get(`post`);
        console.log('Get all posts:', response.data);
        return response.data;
    } catch (error: any) {
        console.error('Get all posts failed:', error.response?.data || error.message);
        throw error;
    }
}

export const getRecentPosts = async () => {
    try {
        const response = await API.get('post/recent');
        console.log('Get recent posts:', response.data);
        return response.data;
    } catch (error: any) {
        console.error('Get recent posts failed:', error.response?.data || error.message);
        throw error;
    }
}

export const getPostById = async (post_id: String) => {
    try {
        const response = await API.get(`post/${post_id}`);
        console.log('Get post by id:', response.data);
        return response.data;
    } catch (error: any) {
        console.error('Get post by id failed:', error.response?.data || error.message);
        throw error;
    }
}

export const getInfinitePosts = async ({ page }: { page: number }) => {
    try {
        const response = await API.post('post/infinite', { page });
        return response.data;
    } catch (error: any) {
        console.error('Get infinite posts failed:', error.response?.data || error.message);
        throw error;
    }
};
