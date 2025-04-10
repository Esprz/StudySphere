import axios from 'axios';

// Define the base URL for the API. Use environment variables for flexibility across environments.
const baseURL = process.env.SERVER_BASE_URL || 'http://localhost:5000';

// Create an Axios instance with default configurations.
export const API = axios.create({
    baseURL,
    timeout: 10000, // Optional: Set a timeout for requests (in milliseconds).
});

// Request interceptor: Automatically attach the Authorization token to every request if available.
API.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('accessToken'); // Retrieve the token from localStorage.
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
    (error) => {
        if (error.response?.status === 401) {
            console.error('Unauthorized, redirecting to login...'); 
            // Handle 401 errors (e.g., redirect to login or clear user session).
        }
        return Promise.reject(error); // Pass the error to the caller for further handling.
    }
);