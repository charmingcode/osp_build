#!/usr/bin/env python
import sys
import os
from osp_util import *
import cmd_base
import docker


class Tool(cmd_base.CommandTool):
  def __init__(self, env):
    cmd_base.CommandTool.__init__(self, env, "ssh", "ssh to one of my running containers", [
        ('n', 'container-name', 'the name of my container', ""),
        ('p', 'option', 'the options of ssh', "-Y"),
        ('c', 'command', 'command to execute', "")
    ])

  def main(self):
    env = self.env
    env.container_name = docker.get_container_name(self)
    env.port = docker.find_port(env)
    command = self.get_opt('command')
    option = self.get_opt('option')
    cmd = "ssh %s %s@`hostname` -p %s" % (option, env.me, env.port)
    print cmd + " ..."
    if command != "":
      cmd += " \"" + command + "\""
    ret = os.system(cmd)
    ret >>= 8
    return ret

