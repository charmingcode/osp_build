#!/usr/bin python
import getopt
import os
import sys
import time
sys.path.insert(1, sys.path[0] + "/lib")
sys.path.insert(1, sys.path[0] + "/commands")
from osp_util import *
import cmd_base
# sys.setdefaultencoding('utf-8')


class Config:
    pass


def init(env):
    path = os.path.join(env.root, "conf", "env.json")
    content = read_file(path)
    conf = eval(content)
    for k in conf:
        exec "env." + k + " = conf[\"" + k + "\"]"
    pass

def finish():
    pass


def main():
    try:
        log_platform()
        log_set_show_date(False)
        log_set_show_pid(False)
        log_set_show_tid(False)
        log_set_show_src(False)
        log_set_show_verbose(False)
        log_set_show_stack(True)

        env = Config()
        env.root = sys.path[0]
        me = whoami()
        if me == "root":
            err("Don't use root run this script")
            return 1

        env.me = me
        env.home = os.environ["HOME"]
        env.cmds = []
        env.osp_build_version = '0'
        # env.image_id = ""
        # env.image_tag = ""
        init(env)
        log_object(env)
        return cmd_base.run_tool(env, "osp.py", "OSP build tool 1.0.%s" % env.osp_build_version)

    except getopt.GetoptError, e:
        err(str(e))
    except Exception, e:
        stack = full_stack()
        err("Exception raised: " + str(e) + "\n" + stack)
        print(str(e))

    finally:
        finish()
        pass


sys.exit(main())
