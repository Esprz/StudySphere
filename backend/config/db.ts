import { Pool } from 'pg';

interface DbConfig {
    user: string;
    host: string;
    database: string;
    password?: string;
    port: number;
}

const dbConfig: DbConfig = {
    user: process.env.DB_USER ?? '',
    host: process.env.DB_HOST ?? '',
    database: process.env.DB_NAME ?? '',
    port: Number(process.env.DB_PORT) || 5432,
};

const pool = new Pool(dbConfig);

export default pool;