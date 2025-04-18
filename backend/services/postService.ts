import prisma from '../utils/prisma';

export const getAllPosts = async () => {
    try {
        return await prisma.post.findMany({
            orderBy: { updated_at: 'desc' },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
        });
    } catch (error) {
        console.error('Error fetching all posts:', error);
        throw new Error('Failed to fetch all posts');
    }
};

export const getPostById = async (post_id: string) => {
    try {
        return await prisma.post.findUnique({
            where: { post_id },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
        });
    } catch (error) {
        console.error('Error fetching post by ID:', error);
        throw new Error('Failed to fetch post by ID');
    }
};

export const getPostByUser = async (username: string) => {
    try {
        return await prisma.post.findMany({
            where: {
                user: {
                    username,
                }
            },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
        });
    } catch (error) {
        console.error('Error fetching posts by user:', error);
        throw new Error('Failed to fetch posts by user');
    }
};

export const getFolloweePosts = async (user_id: string) => {
    try {
        return await prisma.post.findMany({
            where: {
                user: {
                    followers: {
                        some: {
                            follower: {
                                user_id: user_id, // Match the current user's username
                            },
                        },
                    },
                },
            },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
            take: 20,
            orderBy: {
                created_at: 'desc', // Sort by the most recent posts
            },
        });
    } catch (error) {
        console.error('Error fetching followee posts:', error);
        throw new Error('Failed to fetch followee posts');
    }
};

export const getFriendsPosts = async (user_id: string) => {
    try {
        return await prisma.post.findMany({
            where: {
                user: {
                    followers: {
                        some: {
                            follower: {
                                user_id: user_id, // Current user is following this user
                                following: {
                                    some: {
                                        followee: {
                                            user_id: user_id, // This user is also following the current user
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
            take: 20,
            orderBy: {
                created_at: 'desc', // Sort by the most recent posts
            },
        });
    } catch (error) {
        console.error('Error fetching friends posts:', error);
        throw new Error('Failed to fetch friends posts');
    }
};


export const createPost = async (data: {
    title: string;
    content: string;
    user_id: string;
    image?: object;
    extra?: object;
}) => {
    try {
        return await prisma.post.create({ data });        
    } catch (error) {
        console.error('Error creating post:', error);
        throw new Error('Failed to create post');        
    }    
};

export const updatePost = async (
    post_id: string,
    data: { title?: string; content?: string; image?: object; extra?: object }
) => {
    try {
        return await prisma.post.update({
            where: { post_id },
            data,
        });        
    } catch (error) {
        console.error('Error updating post:', error);
        throw new Error('Failed to update post');        
    }    
};

export const deletePost = async (post_id: string) => {
    console.log('Deleting post with ID:', post_id);
    try {
        return await prisma.post.delete({ where: { post_id } });
    } catch (error) {
        console.error('Error deleting post:', error);
        throw new Error('Failed to delete post');
    }
};

export const getRecentPosts = async () => {
    try {
        return await prisma.post.findMany({
            take: 20,
            orderBy: { updated_at: 'desc' },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
        });        
    } catch (error) {
        console.error('Error fetching recent posts:', error);
        throw new Error('Failed to fetch recent posts');        
    }
};


export const searchPosts = async (searchTerm: string) => {
    try {
        return await prisma.post.findMany({
            where: {
                content: {
                    contains: searchTerm,
                    mode: 'insensitive',
                },
            },
            orderBy: { updated_at: 'desc' },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
        });        
    } catch (error) {
        console.error('Error searching posts:', error);
        throw new Error('Failed to search posts');        
    }
};

export const getPaginatedPosts = async (page: number, limit: number = 10) => {
    try {
        return await prisma.post.findMany({
            skip: page * limit,
            take: limit,
            orderBy: { updated_at: 'desc' },
            include: {
                user: {
                    select: {
                        display_name: true,
                        username: true,
                        avatar_url: true,
                    },
                },
            },
        });        
    } catch (error) {
        console.error('Error fetching paginated posts:', error);
        throw new Error('Failed to fetch paginated posts');        
    }
};
