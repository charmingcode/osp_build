#!/usr/bin/env python
import sys
import os
from osp_util import *
import cmd_base
import docker


class Tool(cmd_base.CommandTool):
  def __init__(self, env):
    cmd_base.CommandTool.__init__(self, env, "status",
                                  "list my containers status", []
                                  )

  def main(self):
    env = self.env
    lst = docker.list_containers(self.env)
    file = os.path.join(env.home, ".osp", "container_port_mapping.json")
    mapping = {}
    if os.path.exists(file):
      mapping = load_json_f(file)

    if lst > 0:
      for item in lst:
        id = item[0]
        name = item[1]
        if name.startswith(env.me + "_"):
          if name in mapping:
            print id + " " + name[len(env.me) + 1:] + " " + str(mapping[name])
          else:
            print id + " " + name[len(env.me) + 1:]
    return 0
