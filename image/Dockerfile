FROM ubuntu:focal

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y \
    bluez \
    build-essential \
    ca-certificates \
    cmake \
    dirmngr \
    freetds-bin \
    freetds-dev \
    git \
    gnupg \
    gosu \
    krb5-user \
    ldap-utils \
    libavcodec-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavutil-dev \
    libcurl4-openssl-dev \
    libffi-dev \
    libgraphviz-dev \
    libkrb5-dev \
    libldap2-dev \
    libmysqlclient-dev \
    libpcap-dev \
    libpq-dev \
    libsasl2-2 \
    libsasl2-dev \
    libsasl2-modules \
    libssl-dev \
    libswresample-dev \
    libswscale-dev \
    libturbojpeg0-dev \
    libudev-dev \
    libxml2 \
    libyaml-dev \
    locales \
    lsb-release \
    nano \
    nodejs \
    openssh-client \
    pkg-config \
    postgresql-client \
    python3-pip \
    python3-selinux \
    python3.9 \
    python3.9-dev \
    sasl2-bin \
    software-properties-common \
    sqlite3 \
    unixodbc \
    unixodbc-dev \
    virtualenv \
    yarn

WORKDIR /root

COPY pytest-flakefriend ./pytest-flakefriend
COPY requirements.txt ./requirements.txt
COPY requirements ./requirements
COPY tasks ./tasks

RUN ["/usr/bin/python3.9", "-m", "pip", "install", "-r", "requirements.txt"]

ENTRYPOINT ["/usr/bin/python3.9"]