import { API } from './config';

// Create a comment on a post
export const createComment = async (post_id: string, content: string, parent_id?: string) => {
    try {
        const response = await API.post(`/comment/${post_id}`, {
            content,
            parent_id,
        });
        return response.data; // Returns the created comment
    } catch (error: any) {
        console.error('Error creating comment:', error.response?.data || error.message);
        throw error;
    }
};

// Delete a comment
export const deleteComment = async (comment_id: string) => {
    try {
        const response = await API.delete(`/comment/${comment_id}`);
        return response.data; // Returns success message
    } catch (error: any) {
        console.error('Error deleting comment:', error.response?.data || error.message);
        throw error;
    }
};

// Get comments for a post
export const getCommentsByPost = async (post_id: string) => {
    try {
        const response = await API.get(`/comment/${post_id}`);
        return response.data; // Returns a list of comments for the post
    } catch (error: any) {
        console.error('Error fetching comments:', error.response?.data || error.message);
        throw error;
    }
};