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

CMD ["npm", "run", "dev"]
