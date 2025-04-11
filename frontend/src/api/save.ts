import { API } from "./config";

export const savePost = async (post_id: string) => {
    try {
        const res = await API.post(`/save/${post_id}`);
        return res.data;

    } catch (error) {
        console.error("Error liking post:", error);
        throw error;   
    }    
}
export const deleteSave = async (save_id: string) => {
    try {
        const res = await API.delete(`/save/${save_id}`);
        return res.data;
    } catch (error) {
        console.error("Error deleting save:", error);
        throw error;
    }
}
export const getSavedPosts = async () => {
    try {
        const res = await API.get(`/save`);
        return res.data;
    } catch (error) {
        console.error("Error fetching saved posts:", error);
        throw error;
    }
}