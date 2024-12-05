import { getCurrentUser } from '@/api';
import { PUser } from '@/types/postgresTypes';
import { createContext, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export const INITIAL_USER = {
    user_id: "",
    name: "",
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
    user: PUser;
    isLoading: boolean;
    isAuthenticated: boolean;
    logout: () => Promise<void>;
    checkAuthUser: () => Promise<boolean>;
}


const AuthContext = createContext<AuthContextType>(INITIAL_STATE)

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<PUser>(INITIAL_USER);
    const [isLoading, setisLoading] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const navigate = useNavigate();

    const checkAuthUser = async () => {
        try {            
            const token = localStorage.getItem("token");
            if (!token) {
                navigate("/sign-in");
                return false;
            }
            setisLoading(true);
            const currentUser = await getCurrentUser();
            setUser({
                user_id: currentUser.user_id,
                name: currentUser.username,
                email: currentUser.email,
                avatarUrl: currentUser.avatar_url,
                bio: currentUser.bio,
            });
            setIsAuthenticated(true);
            navigate("/");
            return true;

        } catch (error) {
            console.error("Auth check failed:", error);
            return false;
        } finally {
            setisLoading(false);
        }
    };

    const logout = async () => {
        //console.log('logout');
        localStorage.removeItem("token");
        setUser(INITIAL_USER);
        setIsAuthenticated(false);
        navigate("/sign-in");
    }

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