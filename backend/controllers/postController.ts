import pool from '../config/db';

/*------------------- Post Actions -------------------*/

export const createPost = async (req: any, res: any) => {
    try {
        const { content, image, author } = req.body;
        const newPost = await pool.query(
            "INSERT INTO posts (content, image, author) VALUES($1, $2, $3) RETURNING *",
            [content, image, author]
        );
        res.status(201).json(newPost.rows[0]); // Return created post
    } catch (error: any) {
        res.status(409).json({ message: error.message });
    }
};

export const updatePost = async (req: any, res: any) => {
    console.log('reach updatePost')
    try {
        const { post_id } = req.params;
        const { content, image, author } = req.body;
        const updatedPost = await pool.query(
            `UPDATE posts 
             SET content = $1, image = $2, updated_at = NOW() 
             WHERE post_id = $3
             RETURNING *`,
            [content, image, post_id]
        );

        res.status(200).json(updatedPost.rows[0]); // Return updated post
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

export const deletePost = async (req: any, res: any) => {
    console.log('reach deletePost')
    try {
        const { post_id } = req.params;

        await pool.query(
            "DELETE FROM posts WHERE post_id = $1",
            [post_id]
        );

        res.status(200).json({ message: 'Post deleted successfully!' });
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

export const getPostById = async (req: any, res: any) => {
    console.log('reach getPostById')
    try {
        const { post_id } = req.params;
        const post = await pool.query(
            "SELECT * FROM Posts WHERE post_id = $1;",
            [post_id]
        );
        //console.log('getPostById post_id:', post_id)
        //console.log('getPostById post:', post)
        res.status(200).json(post.rows[0]);
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

export const getAllPosts = async (req: any, res: any) => {
    try {
        const posts = await pool.query("SELECT * FROM posts");
        res.status(200).json(posts.rows);
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

export const getRecentPosts = async (req: any, res: any) => {
    console.log('reach getRecentPosts')
    try {
        const query = `
            SELECT 
                p.*, 
                u.avatar_url AS author_avatar, 
                u.display_name AS author_name 
            FROM 
                Posts p
            JOIN 
                Users u 
            ON 
                p.author = u.user_id 
            ORDER BY 
                p.updated_at DESC 
            LIMIT 20
        `;
        const posts = await pool.query(query);
        res.status(200).json(posts.rows);
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

/*------------------- Like Actions -------------------*/

export const likePost = async (req: any, res: any) => {
    try {
        const { post_id } = req.params;
        const { user_id } = req.body;

        if (!req.userId) {
            return res.status(401).json({ message: 'Unauthenticated' });
        }

        const ifLiked = await pool.query("SELECT * FROM likes WHERE post = $1 AND creator = $2", [post_id, user_id]);

        const like = await pool.query(
            "INSERT INTO likes (post, creator) VALUES($1, $2) RETURNING *",
            [post_id, user_id]
        );

        res.status(201).json(like.rows[0]); // Return created like
    } catch (error: any) {
        res.status(409).json({ message: error.message });
    }
};

export const deleteLike = async (req: any, res: any) => {
    try {
        const { post_id, like_id } = req.params;

        await pool.query(
            "DELETE FROM likes WHERE like_id = $1",
            [like_id]
        );

        res.status(200).json({ message: 'Like deleted successfully!' });
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

export const getLikedPosts = async (req: any, res: any) => {
    try {
        const { user_id } = req.params;
        const likedPosts = await pool.query(
            `SELECT * FROM posts As p
             JOIN likes As l ON p.post_id = l.post
             WHERE l.creator = $1;`,
            [user_id]
        );
        res.status(200).json(likedPosts.rows);
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

/*------------------- Save Actions -------------------*/

export const savePost = async (req: any, res: any) => {
    try {
        const { post_id } = req.params;
        const { user_id } = req.body;

        const save = await pool.query(
            "INSERT INTO saves (post, creator) VALUES($1, $2) RETURNING *",
            [post_id, user_id]
        );

        res.status(201).json(save.rows[0]); // Return created save
    } catch (error: any) {
        res.status(409).json({ message: error.message });
    }
};

export const deleteSave = async (req: any, res: any) => {
    try {
        const { post_id, save_id } = req.params;

        await pool.query(
            "DELETE FROM saves WHERE save_id = $1",
            [save_id]
        );

        res.status(200).json({ message: 'Save deleted successfully!' });
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    };
};

export const getSavedPosts = async (req: any, res: any) => {
    try {
        const { user_id } = req.params;
        const savedPosts = await pool.query(
            `SELECT * FROM posts As p
            JOIN Saves As s ON p.post_id = s.post
            WHERE l.creator = $1;`,
            [user_id]
        );
        res.status(200).json(savedPosts.rows);
    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};
