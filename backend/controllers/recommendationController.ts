import { Request, Response } from 'express';
import axios from 'axios';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS } from '../constants/errorMessages';

const RECOMMENDER_API_URL = process.env.RECOMMENDER_API_URL || 'http://recommender:8000';

export const getSimilarPosts = async (req: Request, res: Response): Promise<void> => {
  try {
    const { post_id } = req.params;
    
    // Call the recommender system API
    const response = await axios.get(`${RECOMMENDER_API_URL}/recommendations/similar-posts/${post_id}`);
    
    res.status(HTTP.OK.code).json(response.data);
  } catch (error) {
    console.error('Error fetching recommendations:', error);
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};