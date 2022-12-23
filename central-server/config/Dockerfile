FROM alpine/git:latest
LABEL maintainer="etancik@gmail.com"

RUN cd ~
RUN git init
RUN git remote add -f origin https://github.com/etancik/home-automation.git
RUN git sparse-checkout init
RUN git sparse-checkout add "central-server/docker-compose/"
RUN git sparse-checkout add "central-server/initial-config/"
RUN git pull origin master
