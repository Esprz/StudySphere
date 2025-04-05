// constants/errorMessages.ts

export const POST_ERRORS = {
  NOT_FOUND: 'Post not found.',
  MISSING_FIELDS: 'Missing required fields.',
  UNAUTHORIZED: 'You are not allowed to modify this post.',
};

export const USER_ERRORS = {
  NOT_FOUND: 'User not found.',
  ALREADY_EXISTS: 'User already exists.',
};

export const GENERAL_ERRORS = {
  UNKNOWN: 'An unexpected error occurred.',
  MISSING_FIELDS: 'Missing required fields.',
};

export const LIKE_ERRORS = {
  ALREADY_LIKED: 'Post already liked.',
  NOT_FOUND: 'Like not found.',
};

export const SAVE_ERRORS = {
  ALREADY_SAVED: 'Post already saved.',
  NOT_FOUND: 'Save not found.',
};
