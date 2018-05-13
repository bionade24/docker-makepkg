FROM archimg/base

RUN echo -e "[multilib]\nInclude = /etc/pacman.d/mirrorlist" >> /etc/pacman.conf
RUN pacman -Syuq --noconfirm --needed gcc base-devel distcc python git mercurial bzr subversion openssh && rm -rf /var/cache/pacman/pkg/*
RUN useradd -m -d /build -s /bin/bash build-user
ADD sudoers /etc/sudoers
WORKDIR /build
VOLUME "/src"
ADD run.py /run.py

ENTRYPOINT ["/run.py"]
