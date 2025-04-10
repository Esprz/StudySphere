import { API, setAccessToken } from './config';
import { PNewUser } from '@/types/postgresTypes';

export const signIn = async (user: { email: string; password: string }) => {
    try {
        const response = await API.post('/auth/sign-in', {
            email: user.email,
            password: user.password,
        });
        /*
        response.data = { user, accessToken }
        */
        if (!response.data || !response.data.accessToken) {
            throw new Error('No access token received');
        }
        setAccessToken(response.data.accessToken);

        return response.data.user;

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
        response.data = { user, accessToken }
        */
        if (!response.data || !response.data.accessToken) {
            throw new Error('No access token received');
        }
        setAccessToken(response.data.accessToken);
        
        return response.data.user;

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
        const response = await API.get('/auth/refresh-token');
        /*
        response.data = { accessToken }
        */
        if (!response.data || !response.data.accessToken) {
            throw new Error('No access token received');
        }
        setAccessToken(response.data.accessToken);
        
    } catch (error: any) {
        console.error('Refresh token failed:', error.response?.data || error.message);
        throw error;
    }
};

export const logOut = async () => {
    try {
        await API.get('/auth/logout');
        setAccessToken(null);
        window.location.href = '/login';

    } catch (error: any) {
        console.error('Log out failed:', error.response?.data || error.message);
        throw error;
    }
};