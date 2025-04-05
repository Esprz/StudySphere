/** @type {import('ts-jest').JestConfigWithTsJest} **/
module.exports = {
  preset: 'ts-jest',
  testEnvironment: "node",
  testMatch: ['**/tests/**/*.test.ts', '**/tests/**/*.spec.ts'], // Match `.test.ts` or `.spec.ts` files in the `tests` folder
  transform: {
    "^.+\.tsx?$": ["ts-jest",{}],
  },
  silent: false
};