import pool from '../config/db';

const getPosts = (req: any, res: any) => {
    try {
        res.status(200).json({ message: 'Posts fetched successfully!' });
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

const createPost = async (req: any, res: any) => {
    try {
        const { title, content, images, author } = req.body;

        const newPost = await pool.query(
            "INSERT INTO posts (title, content, images, author) VALUES($1, $2, $3, $4) RETURNING *",
            [title, content, images, author]
        );

        res.status(201).json(newPost.rows[0]); // Return created post
    } catch (error: any) {
        res.status(409).json({ message: error.message });
    }
};

export { getPosts, createPost };
