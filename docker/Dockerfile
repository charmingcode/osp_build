#Note:
# cd osp/docker && docker build -t osp:test .
# docker run -it --rm -h debug  --privileged  -v $HOME/work/ant/osp/osp:/v -v $HOME/.cache:/root/.cache -w /v/osp   osp:test

#FROM centos:latest
FROM centos:7

#RUN yum install -y yum-plugin-ovl

# Install system tools
RUN yum install -y which vim tree wget net-tools.x86_64 sudo

# Install ssh
RUN yum install -y openssh-server libaio libnsl

# Install gcc
RUN yum install -y glibc glibc-devel
RUN yum install -y gcc gcc-c++ libstdc++-devel binutils gdb

RUN yum install bison

# Install pcre
RUN yum install -y pcre pcre-devel

# Install clang
RUN yum install -y llvm clang compiler-rt

# Install jdk and python 
RUN yum install -y java-1.8.0-openjdk* python36 python27
RUN yum install -y git automake libtool make.x86_64 cmake.x86_64 patch

# Install tools for integration test (aovid net timeout)
#RUN pip3 install pytest py4j pyyaml

# Install bazel
#RUN curl https://copr.fedorainfracloud.org/coprs/vbatts/bazel/repo/epel-7/vbatts-bazel-epel-7.repo -o /etc/yum.repos.d/CentOS-Bazek.repo && yum install -y bazel3

# Install seastar 
COPY install-dependencies.sh .
RUN ./install-dependencies.sh

# Config bashrc/bash_profile
RUN echo "alias ls='ls --color=auto'" >> /root/.bashrc
RUN echo "alias vi='vim'" >> /root/.bashrc
#RUN cd /usr/bin && ln -s python2 python && cd -

#ENTRYPOINT [ "/bin/bash" ]
#ENTRYPOINT ["/bin/bash", "-l", "-c"]