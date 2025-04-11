import { API } from "./config";

export const likePost = async (post_id: string) => {
    try {
        const res = await API.post(`/like/${post_id}`);
        return res.data;

    } catch (error) {
        console.error("Error liking post:", error);
        throw error;   
    }    
}
export const deleteLike = async (like_id: string) => {
    try {
        const res = await API.delete(`/like/${like_id}`);
        return res.data;
    } catch (error) {
        console.error("Error deleting like:", error);
        throw error;
    }
}
export const getLikedPosts = async () => {
    try {
        const res = await API.get(`/like`);
        return res.data;
    } catch (error) {
        console.error("Error fetching liked posts:", error);
        throw error;
    }
}