import { API } from "./config";

export const getUserInfo = async (username: string) => {
    try {
        const response = await API.post("/user", 
            { username:username },
            { withCredentials: true });
        //console.log('server:currentUser:', response);
        return response.data;

    } catch (error: any) {
        console.error("Get user info failed:", error.response?.data || error.message);
        throw error;
    }
};
