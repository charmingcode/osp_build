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

RUN yum install -y flex bison

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


# Install kube

# RUN curl -LO https://dl.k8s.io/release/v1.21.3/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl

# Install seastar 
COPY install-dependencies.sh .
RUN ./install-dependencies.sh

# Install hbase
COPY hbase-2.1.3-bin.tar.gz .
RUN tar zxvf hbase-2.1.3-bin.tar.gz -C /usr/local

# wtty
# 安装依赖
RUN yum -y install vim-common cmake json-c-devel libwebsockets-devel openssl-devel wget make
# 安装libwebsockets
# RUN wget https://github.com/warmcat/libwebsockets/archive/v2.0-stable.tar.gz
COPY libwebsockets-2.0-stable.tar.gz .
RUN tar -zxvf libwebsockets-2.0-stable.tar.gz \
    && cd /libwebsockets-2.0-stable && mkdir build && cd build && cmake .. -DLIB_SUFFIX=64 && make && make install
# 安装ttyd
RUN  wget https://github.com/tsl0922/ttyd/archive/1.2.1.tar.gz \
    && tar -xvzf 1.2.1.tar.gz -C ./ \
    && cd ttyd-1.2.1 \
    &&  mkdir build && cd build &&  pwd
RUN cd /ttyd-1.2.1/build  && echo "CMAKE_C_FLAGS:STRING=--std=c99"  >> ./CMakeCache.txt \
    && cmake .. && make && make install && rm -rf /*.gz

COPY wtty .
RUN mv wtty /usr/bin/

# Config bashrc/bash_profile
# RUN echo "alias ls='ls --color=auto'" >> /root/.bashrc
# RUN echo "alias vi='vim'" >> /root/.bashrc
#RUN cd /usr/bin && ln -s python2 python && cd -

#ENTRYPOINT [ "/bin/bash" ]
#ENTRYPOINT ["/bin/bash", "-l", "-c"]