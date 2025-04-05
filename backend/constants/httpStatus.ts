// constants/httpStatus.ts

export const HTTP = {
  OK: { code: 200, message: 'Success' },
  CREATED: { code: 201, message: 'Created successfully' },
  NO_CONTENT: { code: 204, message: 'No content' },

  BAD_REQUEST: { code: 400, message: 'Invalid request' },
  UNAUTHORIZED: { code: 401, message: 'Unauthorized access' },
  FORBIDDEN: { code: 403, message: 'Forbidden' },
  NOT_FOUND: { code: 404, message: 'Not found' },
  CONFLICT: { code: 409, message: 'Conflict or duplicate' },

  INTERNAL_ERROR: { code: 500, message: 'Internal server error' },
};
