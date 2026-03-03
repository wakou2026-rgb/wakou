FROM node:22-alpine as build-stage

WORKDIR /app
RUN corepack enable
RUN corepack prepare pnpm@latest --activate

RUN npm config set registry https://registry.npmmirror.com

COPY .npmrc package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM alpine:3.21 as production-stage

COPY --from=build-stage /app/dist /dist

CMD ["sh", "-c", "cp -r /dist/. /shared && echo 'Admin dist copied to volume'"]