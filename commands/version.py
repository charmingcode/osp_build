
#!/usr/bin python
import sys
import os
from osp_util import *
import cmd_base


class Tool(cmd_base.CommandTool):
  def __init__(self, env):
    cmd_base.CommandTool.__init__(self, env, "version", "show osp-build version", [
    ])

  def main(self):
    env = self.env
    print "1.0.%s" % env.osp_build_version
    return 0


