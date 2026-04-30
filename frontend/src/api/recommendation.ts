import { API } from './config';

export const getRecommendedFeed = async (limit: number = 20) => {
  try {
    const response = await API.get('recommendations/feed', { params: { limit } });
    return response.data;
  } catch (error: any) {
    console.error('Get recommended feed failed:', error.response?.data || error.message);
    throw error;
  }
};

export const getRecommendedUsers = async (limit: number = 5) => {
  try {
    const response = await API.get('recommendations/users', { params: { limit } });
    return response.data;
  } catch (error: any) {
    console.error('Get recommended users failed:', error.response?.data || error.message);
    throw error;
  }
};
