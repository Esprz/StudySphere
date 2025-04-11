export type PNewPost = {
    title: string;
    content: string;
    images: File[];
    extra: object;
    author: string;
};

export type PUpdatedPost = {
    post_id: string;

    content: string;
    images: File[];
    author: string;
    
    image: string;
    
};

export type PPost = {
    created_at: string;
    updated_at: string;
    post_id: string;
    title: string;
    content: string;
    image: string;
    author: string;
    author_avatar: string;
    author_name: string;
}

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