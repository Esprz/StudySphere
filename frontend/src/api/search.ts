import { API } from './config';

// Search posts by query
export const searchPosts = async (query: string) => {
    try {
        const response = await API.get(`/search`, { params: { q: query } });
        return response.data; // Returns a list of posts matching the query
    } catch (error: any) {
        console.error('Error searching posts:', error.response?.data || error.message);
        throw error;
    }
};