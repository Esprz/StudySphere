import axios from 'axios';
import { refreshToken } from './auth';

// Define the base URL for the API. Use environment variables for flexibility across environments.
const baseURL = import.meta.env.SERVER_BASE_URL || 'http://localhost:5000';

// Create an Axios instance with default configurations.
export const API = axios.create({
    baseURL,
    timeout: 10000, // Set a timeout for requests (in milliseconds).
});

let accessToken: string | null = null; // Store accessToken in memory

export const setAccessToken = (token: string | null) => {
    accessToken = token;
};

export const getAccessToken = () => {
    return accessToken;
};

// Request interceptor: Automatically attach the Authorization token to every request if available.
API.interceptors.request.use(
    (config) => {
        const token = getAccessToken(); // Retrieve the access token from memory.
        if (token) {
            config.headers.Authorization = `Bearer ${token}`; // Add the token to the request headers.
        }
        return config; // Return the modified config.
    },
    (error) => {
        return Promise.reject(error); // Handle request errors.
    }
);

// Response interceptor: Handle responses and errors globally.
API.interceptors.response.use(
    (response) => response, // Pass through successful responses.
    async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401  && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                await refreshToken();
                // Get the new access token after refreshing.
                const newAccessToken = getAccessToken(); 
                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                // Retry the original request with the new token.
                return API(originalRequest); 
                
            } catch (refreshError) {
                console.error('Unauthorized and failed to refresh token:', refreshError);
                window.location.href = '/login';
            }
        }

        return Promise.reject(error); // Pass the error to the caller for further handling.
    }
);