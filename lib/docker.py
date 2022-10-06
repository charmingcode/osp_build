
#!/usr/bin/env python
import json
import os
import re
import socket
import fcntl
from osp_util import *


def is_in_docker():
    return "OSP_DOCKER_IMAGE_TAG" in os.environ


def list_containers(env):
    cmd = "sudo docker ps -a|grep \" %s_\"" % (env.me)
    content = runex(cmd, assert_ok=False).strip()

    lines = content.split("\n")
    lst = []
    for line in lines:
        tokens = line.split(" ")
        # [container_id, container_name]
        id = tokens[0].strip()
        name = tokens[-1].strip()
        if id and name:
            lst.append([id, name])
    return lst

# [[tag, image_id], [tag, image_id] ...]


def list_images(env):
    cmd = "sudo docker images"
    if is_in_docker():
        cmd = "ssh localhost '%s'" % cmd

    content = runex(cmd, assert_ok=False).strip()
    lines = content.split('\n')
    lst = []
    for line in lines:
        line = line.strip()
        if line.find(env.image_repostory) >= 0:
            tokens = line.split()
            if len(tokens) < 3:
                fatal("invalid line " + line)
            lst.append([tokens[1], tokens[2]])

    return lst


def prepare_account(env):
    if is_mac_platform():
        run("echo \"%s:x:1314676:100::/home/%s:/bin/bash\" > %s/.osp/passwd" % (
            env.me, env.me, env.home))
        run("echo \"staff:x:100\" > %s/.osp/group" % (env.home))
    else:
        run("cat /etc/passwd | awk -F: '{if ($1==\"'%s'\") {print}}' > %s/.osp/passwd" % (
            env.me, env.home))
        run("cat /etc/group | awk -F: '{if ($3==\"'`id -g %s`'\") {print}}' > %s/.osp/group" % (
            env.me, env.home))


def prepare_ssh(env):
    run("/bin/cp -f %s/.ssh/authorized_keys %s/authorized_keys" %
        (env.home, env.osp_ssh_dir))

    run("sudo /bin/cp -f /etc/ssh/* %s/ && sudo chown %s %s/*" % (env.osp_etc_ssh_dir,
        env.me, env.osp_etc_ssh_dir))

    pub_file = os.path.join(env.home, ".ssh", "id_rsa.pub")
    if os.path.exists(pub_file):
        run("cat %s >> %s/authorized_keys" % (pub_file, env.osp_ssh_dir))

    pub_file = os.path.join(env.home, ".ssh", "id_dsa.pub")
    if os.path.exists(pub_file):
        run("cat %s >> %s/authorized_keys" % (pub_file, env.osp_ssh_dir))


def find_port(env, assert_ok=True):
    path = os.path.join(env.home, ".osp", "container_port_mapping.json")
    mapping = {}
    if not os.path.exists(path):
        if assert_ok:
            err(path + " not exists")
            sys.exit(2)
        else:
            return "0"

    try:
        content = read_file(path)
        mapping = load_json(content)
    except Exception, ex:
        warn("Read file " + path + " fail: " + str(ex))
        run("rm -f " + path)

    if not env.container_name in mapping:
        if assert_ok:
            err(env.container_name + " not exists in file " + path)
            sys.exit(1)
        else:
            return "0"
    return mapping[env.container_name]


def prepare_after_start(env):
    file = os.path.join(env.root, get_tpl_file("docker_after_start.sh.in"))
    content = read_file(file)

    env.port = "0"
    port = int(find_port(env, assert_ok=False))
    if port != 0:
        try:
            sock = socket.socket()
            sock.bind(("", port))
            env.port = str(sock.getsockname()[1])
            sock.close()
        except:
            pass

    if env.port == "0":
        if env.ssh_port != "0":
            env.port = env.ssh_port
        else:
            sock = socket.socket()
            sock.bind(("", 0))
            env.port = str(sock.getsockname()[1])
            sock.close()
            ports = [env.port]

    if is_linux_platform():
        env.group = runex("cat " + env.home +
                          "/.osp/group | awk '{print $1}'").strip()
    content = content.replace("$PORT", env.port)
    content = content.replace("$USER", env.me)
    content = content.replace("$GROUP", env.group)

    output = os.path.join(
        env.home, ".osp", env.container_name + "_docker_after_start.sh")
    write_file(output, content)
    run("chmod +x " + output)


def get_container_name_real(self):
    env = self.env
    container_name = self.get_opt('container-name')
    if not container_name:
        container_name = "dev"
    return container_name


def get_container_name(self):
    env = self.env
    container_name = self.get_opt('container-name')
    tail = ""
    if not container_name:
        container_name = "dev"

    if container_name == "dev":
        pushd()
        cd(env.root, show_log=False)
        branch = runex("git rev-parse --abbrev-ref HEAD",
                       assert_ok=False).strip()
        if branch != "master" and branch != "HEAD":
            tail = "_" + branch
        popd(show_log=False)

    container_name = self.env.me + "_" + container_name + tail
    return container_name


def write_container_port_mapping(env):
    path = os.path.join(env.home, ".osp", "container_port_mapping.json")
    mapping = {}
    lock_file = path + ".lock"
    if not os.path.exists(lock_file):
        run("touch " + lock_file)
    lockf = open(lock_file, "rb")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    if os.path.exists(path):
        content = read_file(path)
        mapping = eval(content)
    mapping[env.container_name] = env.port
    write_file(path, dump_json(mapping))
    fcntl.flock(lockf, fcntl.LOCK_UN)
    lockf.close()


def get_tpl_file(name):
    return os.path.join("tpl", name)


def generate_limits_file(env):
    input = os.path.join(env.root, get_tpl_file("limits.conf.in"))
    output = os.path.join(env.home, ".osp", "limits.conf")

    write_file(output, read_file(input).replace("$USER", env.me))
    return output


def generate_bashrc(env):
    input = os.path.join(env.root, get_tpl_file("bashrc.in"))
    output = os.path.join(env.home, ".osp", env.container_name + "_bashrc")
    run("rm -rf " + output)
    write_file(output, read_file(input).replace(
        "$NAME", env.container_name).replace("$IMAGE_ID", env.image_id))
    return output


def check_core_pattern():
    core_pattern = read_file("/proc/sys/kernel/core_pattern").strip()
    if core_pattern != "/osp/data/corefile/core-%e-%p-%t-%h":
        fatal("core_pattern must be /osp/data/corefile/core-%%e-%%p-%%t-%%h, run '%s' and try again!"
              % green("echo /osp/data/corefile/core-%e-%p-%t-%h|sudo tee /proc/sys/kernel/core_pattern"))


def check_io_setup():
    me = runex("whoami")
    if me == "admin":
        return

    io_setup = int(read_file("/proc/sys/fs/aio-max-nr").strip())
    if io_setup < 1048576:
        fatal("io_setup(%d now) need to set a higher value run '%s' and try again!"
              % (io_setup, green("echo \"1048576\"|sudo tee /proc/sys/fs/aio-max-nr")))


def clone_file(env, file):
    dst_file = os.path.join(
        env.home, ".osp", env.container_name + "_" + uuid_gen())
    if os.path.exists(dst_file):
        run("rm -rf " + dst_file)
    run("cp -rf %s %s" % (file, dst_file))
    return dst_file


def start_docker(env):
    # get mapping from env.json
    if is_linux_platform():
        check_core_pattern()
        check_io_setup()

    core_dir = os.path.join(env.home, ".osp", "corefile", env.container_name)

    mapping = env.mapping
    if os.path.exists("/ospdfs"):
        mapping["/ospdfs"] = "/ospdfs"

    # if os.path.islink("/dump/1"):
    #     dump1dir = runex("readlink -f /dump/1").strip()
    #     mapping[dump1dir] = dump1dir

    work_dir = os.path.join(env.home, "Worker")
    if not os.path.exists(work_dir):
        fatal(
            "%s not found, make a symbol link to a hdd disk to save core files" % work_dir)

    if is_mac_platform():
        size = runex(
            "df -k %s|tail -n 1|awk '{print $4}'" % work_dir, assert_ok=False).strip()
    else:
        size = runex(
            "df %s|tail -n 1|awk '{print $4}'" % work_dir, assert_ok=False).strip()
    info("df %s available %sk" % (work_dir, size))
    min_size = 1024 * 1024 * 10
    if int(size) < min_size:
        fatal("insufficient disk space in %s available %d must > %dk\n" %
              (work_dir, int(size), min_size))
    core_dir = work_dir + "/osp_core_" + env.me + "/data/" + env.container_name

    if not os.path.exists(core_dir):
        make_dir(core_dir, sudo=True)

    if not os.path.exists(core_dir):
        fatal(core_dir + " not exists")

    # mapping home dir
    if is_mac_platform():
        mapping[env.home] = env.home.replace("Users", "home")
    else:
        real_path = runex("readlink -f " + env.home).strip()
        if real_path != env.home:
            mapping[real_path] = env.home
        else:
            mapping[env.home] = env.home

    # home2 = "/home/" + env.me
    # if env.home != home2:
    #     real_path = runex("readlink -f " + home2).strip()
    #     if real_path != home2:
    #         mapping[real_path] = home2
    #     else:
    #         mapping[home2] = home2

    # mapping .bashrc and .bash_profile
    kubeconfig_dir = os.path.join(
        env.home, ".osp", env.container_name + "_kube_config")
    make_dir(kubeconfig_dir)

    home = "/home/" + env.me + "/"
    mapping[generate_bashrc(env)] = home + ".bashrc"
    mapping[clone_file(env, get_tpl_file("bash_profile"))
            ] = home + ".bash_profile"
    mapping[kubeconfig_dir] = home + ".kube"
    mapping[env.root + "/gdb/osp.gdb"] = home + ".gdbinit"

    # Modify the ulimit "open files(-n)" value which can not be modified by "docker --ulimit nofile ...".
    # TODO by charming
    # mapping[generate_limits_file(env)] = "/etc/security/limits.conf"

    # mapping after_start.sh
    mapping[env.home + "/.osp/" + env.container_name +
            "_docker_after_start.sh"] = "/sbin/docker_start.sh"
    # mapping[clone_file(env, os.path.join(env.root, get_tpl_file(
    # "after_start.sh")))] = "/tmp/after_start.sh"

    # other
    mapping[env.home + "/.osp/passwd"] = "/tmp/.passwd"
    mapping[env.home + "/.osp/group"] = "/tmp/.group"
    mapping[env.osp_etc_ssh_dir] = "/etc/ssh"
    mapping["/var/run/docker.sock"] = "/var/run/docker.sock"
    mapping["/etc/hosts"] = "/etc/hosts:ro"
    if is_linux_platform():
        mapping["/root"] = "/root"
        mapping["/etc/sysconfig/network"] = "/etc/sysconfig/network:ro"
        mapping["/etc/sysconfig/network-scripts"] = "/etc/sysconfig/network-scripts:ro"
        
    tmp_dir = os.path.join(env.home, "tmp", uuid_gen())
    run("mkdir -p " + tmp_dir)
    mapping[os.path.abspath(env.root)] = "/usr/local/osp-build"
    run("mkdir -p %s/.osp/repo" % env.home)
    mapping[env.home + "/.osp/repo"] = "/osp/repo"
    mapping[tmp_dir] = "/tmp"
    mapping[core_dir] = "/osp/data/corefile"

    user_mapping_file = os.path.join(env.home, ".osp", "mapping.json")
    if os.path.exists(user_mapping_file):
        user_mapping = eval(read_file(user_mapping_file))
        for key in user_mapping.keys():
            mapping[key] = user_mapping[key]

    iopts = "-it" if env.interactive else "-d"
    cmd = "sudo docker run %s --name %s" % (iopts, env.container_name)

    for opt in env.options:
        if opt.find("--net=host") >= 0 and is_mac_platform():
            cmd += " " + env.nonlinux_port_range
            continue
        cmd += " " + opt

    for key in mapping.keys():
        val = mapping[key]
        key = key.replace("$HOME", env.home)
        key = os.path.realpath(key)
        cmd += " -v %s:%s" % (key, val)

    cmd += " %s /sbin/docker_start.sh" % (env.image)
    run(cmd)
    write_container_port_mapping(env)


def wait_docker_start(env, timeout):
    for i in xrange(0, timeout):
        time.sleep(1)
        lst = list_containers(env)
        for container in lst:
            id = container[0]
            name = container[1]
            if name == env.container_name:
                cmd = "sudo docker exec %s cat /etc/sshd_port" % (id)
                content = runex(cmd, assert_ok=False, show_log=False).strip()
                if content == str(env.port):
                    return 0
                else:
                    info("Wait sshd start : " + content)
    err("sshd in docker start fail")
    return 1
