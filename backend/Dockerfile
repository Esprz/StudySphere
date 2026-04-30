FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY prisma ./prisma
RUN npx prisma generate
# RUN npx prisma migrate dev --name init
# RUN npx prisma migrate reset --force 
# RUN npx prisma studio (see current tables)

COPY . .

EXPOSE 5000

RUN npm install -g pm2
RUN npm run build

CMD ["npx", "pm2-runtime", "start", "ecosystem.config.js"]
