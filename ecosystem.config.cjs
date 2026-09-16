module.exports = {
  apps: [
    {
      name: "deeptrace-api",
      cwd: "/home/ubuntu/DeepTrace",
      script: "/home/ubuntu/DeepTrace/.venv/bin/uvicorn",
      args: "app.main:app --host 127.0.0.1 --port 8000",
      interpreter: "none",
      autorestart: true,
      restart_delay: 2000,
      env: {
        PYTHONPATH: "/home/ubuntu/DeepTrace",
      },
    },
    {
      name: "deeptrace-web",
      cwd: "/home/ubuntu/DeepTrace/frontend",
      script: "node_modules/.bin/next",
      args: "start -p 3000",
      autorestart: true,
      restart_delay: 2000,
      env: {
        NODE_ENV: "production",
        PORT: 3000,
      },
    },
  ],
};
