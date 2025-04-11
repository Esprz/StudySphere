import { API } from './config';

// Follow a user
export const followUser = async (followee_id: string) => {
    try {
        const response = await API.post(`/follow/${followee_id}`);
        return response.data; // Returns the follow relationship data
    } catch (error: any) {
        console.error('Error following user:', error.response?.data || error.message);
        throw error;
    }
};

// Unfollow a user
export const unfollowUser = async (follow_id: string) => {
    try {
        const response = await API.delete(`/follow/${follow_id}`);
        return response.data; // Returns success message
    } catch (error: any) {
        console.error('Error unfollowing user:', error.response?.data || error.message);
        throw error;
    }
};

// Get followers of a user
export const getFollowers = async () => {
    try {
        const response = await API.get(`/follow/followers`);
        return response.data; // Returns a list of followers
    } catch (error: any) {
        console.error('Error fetching followers:', error.response?.data || error.message);
        throw error;
    }
};

// Get followees (users the current user is following)
export const getFollowees = async () => {
    try {
        const response = await API.get(`/follow/followees`);
        return response.data; // Returns a list of followees
    } catch (error: any) {
        console.error('Error fetching followees:', error.response?.data || error.message);
        throw error;
    }
};