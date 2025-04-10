import { API } from './config';
import { PNewUser } from '@/types/postgresTypes';

export const signIn = async (user: { email: string; password: string }) => {
    try {
        const response = await API.post('/auth/sign-in', {
            email: user.email,
            password: user.password,
        });
        /*
        response.data = { user, accessToken, refreshToken }
        */
        localStorage.setItem("accessToken", response.data.accessToken);
        localStorage.setItem("refreshToken", response.data.refreshToken);
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
        /*
        response.data = { user, accessToken, refreshToken }
        */
        localStorage.setItem("accessToken", response.data.accessToken);
        localStorage.setItem("refreshToken", response.data.refreshToken);
        
        return response.data;

    } catch (error: any) {
        console.error('Sign-up failed:', error.response?.data || error.message);
        throw error;
    }
};

export const getCurrentUser = async () => {
    try {
        const response = await API.get("/auth/user");
        //console.log('server:currentUser:', response);
        return response.data;

    } catch (error: any) {
        console.error("Token verification failed:", error.response?.data || error.message);
        throw error;
    }
};

export const refreshToken = async () => {
    try {
        const refreshToken = localStorage.getItem("refreshToken");
        if (!refreshToken) {
            throw new Error("Refresh token not found");
        }
        const response = await API.post('/auth/refresh-token', {
            refreshToken: refreshToken,
        });
        /*
        response.data = { accessToken, refreshToken }
        */
        localStorage.setItem("accessToken", response.data.accessToken);
        localStorage.setItem("refreshToken", response.data.refreshToken);
        return response.data;
    } catch (error: any) {
        console.error('Refresh token failed:', error.response?.data || error.message);
        throw error;
    }
};

export const logOut = async () => {
    try {
        const refreshToken = localStorage.getItem("refreshToken");
        if (!refreshToken) {
            throw new Error("Refresh token not found");
        }
        const response = await API.post('/auth/logout', {
            refreshToken: refreshToken,
        });
        
        // Clear tokens from localStorage
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");

        return response.data;

    } catch (error: any) {
        console.error('Log out failed:', error.response?.data || error.message);
        throw error;
    }
};