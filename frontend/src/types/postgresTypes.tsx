export type PNewPost = {
    title: string;
    content: string;
    images: string[];
    author: number;
};

export type PUpdatedPost = {
    title: string;
    content: string;
    images: string[];
    author: number;
};

export type PNewUser = {
    name: string;
    email: string;
    password: string;
    bio?: string;
    avatar_url?: string;
};

export type PUser = {
    user_id: string;
    name: string;
    email: string;
    avatarUrl?: string;
    bio?: string;
  };