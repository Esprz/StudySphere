import { Pool } from 'pg';

const dbConfig = {
    user: process.env.DB_USER,
    host: process.env.DB_HOST,
    database: process.env.DB_NAME,
    password: String(process.env.DB_PASSWORD),
    port: Number(process.env.DB_PORT),
};

const pool = new Pool(dbConfig);

export default pool;