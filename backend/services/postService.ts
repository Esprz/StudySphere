import prisma from '../utils/prisma';
import { eventService } from './eventService';


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
        const post = await prisma.post.create({ data });
        // console.log('Post created:', post);   
        setImmediate(async () => {
            try {
                await eventService.trackPostCreated(post.post_id, post.user_id, {
                    title: post.title,
                    content: post.content,
                    created_at: post.created_at,
                    
                });
            } catch (error) {
                console.error('Event tracking failed:', error);
            }
        });
        return post;
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
        const post = await prisma.post.update({
            where: { post_id },
            data,
        });
        // console.log('Post updated:', post);
        setImmediate(async () => {
            try {
                await eventService.trackPostUpdated(post_id, post.user_id, {
                    title: post.title,
                    content: post.content,
                    created_at: post.created_at,
                });
            } catch (error) {
                console.error('Event tracking failed:', error);
            }
        });
        return post;
    } catch (error) {
        console.error('Error updating post:', error);
        throw new Error('Failed to update post');
    }
};

export const deletePost = async (post_id: string) => {
    console.log('Deleting post with ID:', post_id);
    try {
        const post = await prisma.post.findUnique({ where: { post_id } });
        if (!post) throw new Error('Post not found');

        const deletedPost = await prisma.post.delete({ where: { post_id } });

        setImmediate(async () => {
            try {
                await eventService.trackPostDeleted(post_id, post.user_id);
            } catch (error) {
                console.error('Event tracking failed:', error);
            }
        });

        return deletedPost;
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
