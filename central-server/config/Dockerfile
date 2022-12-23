FROM alpine/git:latest
LABEL maintainer="etancik@gmail.com"

WORKDIR /git
RUN git init -b master && \ 
git remote add -f origin https://github.com/etancik/home-automation.git && \
git sparse-checkout init && \
git sparse-checkout add "central-server/docker-compose/" && \
git sparse-checkout add "central-server/initial-config/" && \
git pull origin master
