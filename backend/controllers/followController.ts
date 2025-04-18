import { Request, Response } from 'express';
import * as followService from '../services/followService';
import { HTTP } from '../constants/httpStatus';
import { GENERAL_ERRORS, FOLLOW_ERRORS } from '../constants/errorMessages';

export const createFollow = async (req: Request, res: Response): Promise<void> => {
  try {
    const { followee_username } = req.params;
    const user_id = req.userId;

    if (!followee_username || !user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }

    const follow = await followService.createFollow(followee_username, user_id);

    if (!follow) {
      res.status(HTTP.CONFLICT.code).json({ message: FOLLOW_ERRORS.ALREADY_FOLLOWED });
      return;
    }

    res.status(HTTP.CREATED.code).json(follow);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const deleteFollow = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    const { followee_username } = req.params;
    if (!user_id || !followee_username) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }
    await followService.deleteFollow(followee_username, user_id);
    res.status(HTTP.OK.code).json({ message: 'Follow deleted.' });
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getFollowers = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }
    const followers = await followService.getFollowers(user_id);
    res.status(HTTP.OK.code).json(followers);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getFollowees = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }
    const data = await followService.getFollowees(user_id);
    const followees = data.map((follow) => ({
      user_id: follow.followee.user_id,
      username: follow.followee.username,
      display_name: follow.followee.display_name,
      avatar_url: follow.followee.avatar_url,
    }));
    
    res.status(HTTP.OK.code).json(followees);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
};

export const getSuggestedToFollow = async (req: Request, res: Response): Promise<void> => {
  try {
    const user_id = req.userId;
    if (!user_id) {
      res.status(HTTP.BAD_REQUEST.code).json({ message: GENERAL_ERRORS.MISSING_FIELDS });
      return;
    }
    const suggestedFollowees = await followService.getSuggestedToFollow(user_id);
    res.status(HTTP.OK.code).json(suggestedFollowees);
  } catch {
    res.status(HTTP.INTERNAL_ERROR.code).json({ message: GENERAL_ERRORS.UNKNOWN });
  }
}