
#!/usr/bin/env python
import sys
import os
from osp_util import *
import cmd_base
import socket
import docker


class Tool(cmd_base.CommandTool):
  def __init__(self, env):
    cmd_base.CommandTool.__init__(self, env, "stop",
                                  "destroy running containers of holo build", [
                                      ('n', 'container-name', "the name of the container to stop, if not set, stop all", ""),
                                      ('f', 'force', "force to stop", False)
                                  ])

  def rm_files(self, name):
    env = self.env
    run("rm -rf %s/.holo/%s*" % (env.home, name))

  def main(self):
    force = self.get_opt('force')
    lst = docker.list_containers(self.env)
    container_name_exist = (self.get_opt('container-name') != "")
    container_name = docker.get_container_name(self)

    if lst > 0:
      for item in lst:
        id = item[0]
        name = item[1]
        if container_name_exist:
          if container_name == name:
            run("sudo docker rm -f " + name)
            self.rm_files(name)
            return 0
        else:
          if force:
            run("sudo docker rm -f " + name)
            self.rm_files(name)
          else:
            print "Stop [%s] [%s] Y|N?" % (id, name)
            sys.stdout.flush()
            answer = sys.stdin.readline().strip().lower()
            if answer == "y":
              run("sudo docker rm -f " + name)
              self.rm_files(name)

    if not force and container_name_exist:
      err("container " + container_name + " not found")
      return 2
    return 0

