module.exports = {
  apps: [
    {
      name: 'studysphere-backend',
      script: 'dist/server.js',
      instances: process.env.PM2_INSTANCES || 'max',
      exec_mode: 'cluster',
      env: {
        NODE_ENV: process.env.NODE_ENV || 'production',
      },
    },
  ],
};
