import prisma from '../utils/prisma';

export const getAllPosts = async () => {
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
};

export const getPostById = async (post_id: string) => {
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
};

export const getPostByUser = async (username: string) => {
    return await prisma.post.findMany({
        where: {
            user: {
                username,
            }
        },
    });
};

export const createPost = async (data: {
    title: string;
    content: string;
    user_id: string;
    image?: object;
    extra?: object;
}) => {
    return await prisma.post.create({ data });
};

export const updatePost = async (
    post_id: string,
    data: { title?: string; content?: string; image?: object; extra?: object }
) => {
    return await prisma.post.update({
        where: { post_id },
        data,
    });
};

export const deletePost = async (post_id: string) => {
    return await prisma.post.delete({ where: { post_id } });
};

export const getRecentPosts = async () => {
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
};


export const searchPosts = async (searchTerm: string) => {
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
};

export const getPaginatedPosts = async (page: number, limit: number = 10) => {
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
};
