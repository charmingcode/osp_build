
#!/usr/bin/env python
import sys
import os
from osp_util import *
import cmd_base
import docker


class Tool(cmd_base.CommandTool):
  def __init__(self, env):
    cmd_base.CommandTool.__init__(self, env, "start",
                                  "start a docker for osp build, if the image doen't exist, pull it first", [
                                      ('I', 'image-id', 'the image id of osp build image, it is only for check', env.image_id),
                                      ('i', 'image-tag', 'the image tag of osp build image', env.image_tag),
                                      ('t', 'interactive', 'set -it to docker', False),
                                      ('n', 'container-name', "the name of the new container, if not set, use `whoami`_dev'", ""),
                                      ('v', 'mapping', "file mapping'", ""),
                                  ])

  def check_container_exist(self):
    env = self.env
    lst = docker.list_containers(env)
    for item in lst:
      id = item[0]
      name = item[1]
      if name == env.container_name:
        err("container [%s] [%s] exists already, stop it first!" % (id, name))
        return True
    return False

  def check_image_exist(self):
    env = self.env
    lst = docker.list_images(env)
    for item in lst:
      tag = item[0]
      id = item[1]
      if tag == env.image_tag:
        return True
    return False

  def check_image_id_match(self):
    env = self.env
    if env.image_id == "":
      return True

    lst = docker.list_images(env)
    for item in lst:
      tag = item[0]
      id = item[1]
      if tag == env.image_tag:
        if id != env.image_id:
          err("the id of image [%s] must be [%s] , it's [%s] now" % (env.image, env.image_id, id))
          cmd = green("sudo docker rmi " + id)
          err("there may be a bad image [%s] on this machine, use \"%s\" to remove it and try again" % (env.image, cmd))
          return False
        return True
    err("image [%s] not found" % (env.image))
    return False

  def main(self):
    env = self.env
    if env_is_true("OSP_NO_AUTO_UPDATE") or not is_linux_platform():
      info("no auto update")
    else:
      info("try to update")
      auto_update(env.root)
      os.environ["OSP_NO_AUTO_UPDATE"] = "1"
      cmd = ""
      for arg in sys.argv:
        if cmd:
          cmd += " "
        arg = arg.replace("\\", "\\\\")
        arg = arg.replace("\"", "\\\"")
        cmd += "\"%s\"" % arg
      info("update end, run <%s> ..." % cmd)
      return ret_code(os.system(cmd))

    env.image_id = self.get_opt('image-id')
    env.image_tag = self.get_opt('image-tag')
    env.image = "%s:%s" % (env.image_repostory, env.image_tag)
    env.container_name = docker.get_container_name(self)
    env.container_name_real = docker.get_container_name_real(self)

    if self.check_container_exist():
      return 1

    env.osp_etc_ssh_dir = os.path.join(env.home, ".osp", "etc", "ssh")
    env.osp_ssh_dir = os.path.join(env.home, ".osp", ".ssh")
    if not os.path.exists(env.osp_etc_ssh_dir):
      os.makedirs(env.osp_etc_ssh_dir)

    if not os.path.exists(env.osp_ssh_dir):
      os.makedirs(env.osp_ssh_dir)

    if not self.check_image_exist():
      run("sudo docker pull %s" % (env.image))

    if not self.check_image_id_match():
      return 1

    docker.prepare_account(env)
    docker.prepare_after_start(env)
    docker.prepare_ssh(env)

    for file_mapping in self.get_opts("mapping"):
      file_mapping = file_mapping.strip()
      if not file_mapping:
        continue
      tokens = file_mapping.split(":")
      if len(tokens) != 2 or not tokens[0] or not tokens[1]:
        fatal("invalid file mapping, need '/path-a:/path-b'")
      env.mapping[tokens[0]] = tokens[1]
    env.interactive = self.get_opt("interactive")
    docker.start_docker(env)
    # time out 30 second
    if docker.wait_docker_start(env, 6) == 0:
      return 0
    return 1

