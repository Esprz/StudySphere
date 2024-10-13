import express, { Express } from 'express';
import cors from 'cors';
import { Pool } from 'pg';

const app: Express = express();

app.use(cors());

