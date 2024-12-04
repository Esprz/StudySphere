import pool from '../config/db';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';


export const signIn = async (req: any, res: any) => {
    try {
        const { email, password } = req.body;
        const existingUser = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
        if (!existingUser.rows.length) {
            return res.status(404).json({ message: "User doesn't exist" });
        }
        //console.log('existingUser.rows[0]:',existingUser.rows[0]);
        const currentUser = existingUser.rows[0];
        //console.log('before password check');
        const isPasswordCorrect = await bcrypt.compare(password, currentUser.password_hash);
        if (!isPasswordCorrect) {
            return res.status(400).json({ message: "Invalid credentials" });
        }
        //console.log('after password check');

        const token = jwt.sign({ email: currentUser.email, id: currentUser.user_id }, 'test', { expiresIn: "1h" });
        res.status(200).json({ result: currentUser, token });

    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};


export const signUp = async (req: any, res: any) => {
    try {
        const { username, display_name, email, password, bio = null, avatar_url = null } = req.body;
        const existingUser = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
        if (existingUser.rows.length) {
            return res.status(400).json({ message: "User already exists" });
        }
        const hashedPassword = await bcrypt.hash(password, 12);
        const newUser = await pool.query(
            `INSERT INTO users 
            (username, display_name, email, password_hash, bio, avatar_url) 
            VALUES ($1, $2, $3, $4, $5, $6) 
            RETURNING *`,
            [username, display_name, email, hashedPassword, bio, avatar_url]);

        const token = jwt.sign({ email: newUser.rows[0].email, id: newUser.rows[0].id }, 'test', { expiresIn: "1h" });
        res.status(200).json({ result: existingUser.rows[0], token });

    } catch (error: any) {
        res.status(404).json({ message: error.message });
    }
};

