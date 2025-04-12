import { getCurrentUser, logOut } from '@/api';
import { getAccessToken } from '@/api/config';
import { PUser } from '@/types/postgresTypes';
import { createContext, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export const INITIAL_USER = {    
    username: "",
    user_id: "",
    name: "",
    display_name: "",
    email: "",
    avatarUrl: "",
    bio: "",
};

export const INITIAL_STATE = {
    user: INITIAL_USER,
    isLoading: false,
    isAuthenticated: false,
    logout: async () => { },
    checkAuthUser: async () => false as boolean,
}

type AuthContextType = {
    user: any;
    isLoading: boolean;
    isAuthenticated: boolean;
    logout: () => Promise<void>;
    checkAuthUser: () => Promise<boolean>;
}


const AuthContext = createContext<AuthContextType>(INITIAL_STATE)

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState(INITIAL_USER);
    const [isLoading, setisLoading] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const navigate = useNavigate();

    const checkAuthUser = async () => {
        try {            
            const token = getAccessToken();
            if (!token) {
                navigate("/sign-in");
                return false;
            }
            setisLoading(true);
            const currentUser = await getCurrentUser();
            setUser({
                username: currentUser.username,
                user_id: currentUser.user_id,
                name: currentUser.display_name,                
                display_name: currentUser.display_name,
                email: currentUser.email,
                avatarUrl: currentUser.avatar_url,
                bio: currentUser.bio,
            });
            setIsAuthenticated(true);
            navigate("/");
            return true;

        } catch (error) {
            console.error("Auth check failed:", error);
            setIsAuthenticated(false);
            return false;
        } finally {
            setisLoading(false);
        }
    };

    const logout = async () => {
        try {
            console.log("Logging out...");
            await logOut(); 
            setUser(INITIAL_USER); 
            setIsAuthenticated(false); 
            navigate("/sign-in"); 
        } catch (error) {
            console.error("Logout failed:", error);
        }
    };

    useEffect(() => {
        //console.log('authcontext useeffect');
        checkAuthUser();
    }, []);

    const value = {
        user,
        isLoading,
        isAuthenticated,
        logout,
        checkAuthUser,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export const useUserContext = () => useContext(AuthContext);