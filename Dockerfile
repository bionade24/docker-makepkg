FROM archimg/base

RUN mkdir -p /build
WORKDIR /build
RUN pacman -Syuq --noconfirm --needed gcc-multilib base-devel distcc && rm -rf /var/cache/pacman/pkg/*
RUN pacman -Syuq --noconfirm --needed git mercurial bzr subversion openssh && rm -rf /var/cache/pacman/pkg/*
RUN echo -e "[multilib]\nInclude = /etc/pacman.d/mirrorlist" >> /etc/pacman.conf
RUN useradd -d /build build-user
ADD sudoers /etc/sudoers
ADD run.sh /run.sh

VOLUME "/src"

ENTRYPOINT ["/run.sh"]
