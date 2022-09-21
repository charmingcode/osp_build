import os
import sys
if sys.version_info.major == 2:
    import commands
elif sys.version_info.major == 3:
    pass
else:
    print("unkown sys.version_info.major: %d" % sys.version_info.major)
    os._exit(1)

import copy
import fcntl
import inspect
import json
import logging
import logging.handlers
import os
import platform
import pwd
import random
import re
import socket
import subprocess
import time
import traceback
import threading
import uuid
from datetime import datetime
from collections import OrderedDict


def full_stack():
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]
    if exc is not None:
        del stack[-1]
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
        stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr


class OpsLogger(logging.Logger):
    def __init__(self, log_name, level=None):
        logging.Logger.__init__(self, log_name)

    def findCaller(self, stack_info=False, stacklevel=1):
        sinfo = None
        f = inspect.currentframe()
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        if f is not None:
            f = f.f_back

        if sys.version_info.major == 2:
            rv = "(unknown file)", 0, "(unknown function)"
        else:
            rv = "(unknown file)", 0, "(unknown function)", sinfo

        stat = 0
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)

            if "/logging/" in filename:
                f = f.f_back
                continue

            _, name = os.path.split(filename)
            if name == "ops_util.py":
                f = f.f_back
                continue

            if sys.version_info.major == 2:
                rv = co.co_filename, f.f_lineno, co.co_name
            else:
                if stack_info:
                    sio = io.StringIO()
                    sio.write('Stack (most recent call last):\n')
                    traceback.print_stack(f, file=sio)
                    sinfo = sio.getvalue()
                    if sinfo[-1] == '\n':
                        sinfo = sinfo[:-1]
                    sio.close()
                rv = co.co_filename, f.f_lineno, co.co_name, sinfo
            break

        f = f.f_back
        return rv


__log_show_date = True
__log_show_pid = False
__log_show_src = True
__log_show_tid = False
__log_show_stack = False
__log_show_verbose = False


def log_set_show_date(val):
    global __log_show_date
    __log_show_date = val


def log_set_show_pid(val):
    global __log_show_pih
    __show_pid = val


def log_set_show_tid(val):
    global __log_show_tid
    __log_show_tid = val


def log_set_show_src(val):
    global __log_show_src
    __log_show_src = val


def log_set_show_verbose(val):
    global __log_show_verbose
    __log_show_verbose = val


def log_set_show_stack(val):
    global __log_show_stack
    __log_show_stack = val


def uuid_gen():
    return str(uuid.uuid1())


def red(s):
    return "\033[1;31;40m" + s + "\033[0m"


def yellow(s):
    return "\033[1;33;40m" + s + "\033[0m"


def green(s):
    return "\033[1;32;40m" + s + "\033[0m"


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


class WarnFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno == logging.WARNING


class ErrorFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno == logging.ERROR


def __get_logger(name, log_file, only_file=False):
    global __log_show_date
    global __log_show_pid
    global __log_show_src
    global __log_show_tid
    global __log_show_verbose

    logger = OpsLogger(name)
    if __log_show_verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if __log_show_date:
        datefmt = '%Y-%m-%d %H:%M:%S'
    else:
        datefmt = '%H:%M:%S'

    formatter = "%(asctime)s ${level}"
    if __log_show_pid:
        formatter += " %(process)d"
    if __log_show_tid:
        formatter += " %(threadName)s"
    formatter += " %(message)s"
    if __log_show_src:
        formatter += " |%(filename)s(%(lineno)d)"

    logfile = os.path.abspath(log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        logfile, maxBytes=100 * 1024 * 1024, backupCount=10)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        formatter.replace("${level}", "%(levelname)s"), datefmt=datefmt))
    logger.addHandler(file_handler)

    if only_file:
        return logger

    info_handler = logging.StreamHandler(sys.stdout)
    info_handler.addFilter(InfoFilter())
    info_handler.setFormatter(logging.Formatter(formatter.replace(
        "${level}", green("%(levelname)s")), datefmt=datefmt))
    logger.addHandler(info_handler)

    warn_handler = logging.StreamHandler(sys.stdout)
    warn_handler.setLevel(logging.WARNING)
    warn_handler.addFilter(WarnFilter())
    logger.addHandler(warn_handler)
    warn_handler.setFormatter(logging.Formatter(formatter.replace(
        "${level}", yellow("%(levelname)s")), datefmt=datefmt))
    logger.addHandler(warn_handler)

    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.addFilter(ErrorFilter())
    error_handler.setFormatter(logging.Formatter(formatter.replace(
        "${level}", red("%(levelname)s")), datefmt=datefmt))
    logger.addHandler(error_handler)

    fatal_handler = logging.StreamHandler(sys.stderr)
    fatal_handler.setLevel(logging.FATAL)
    fatal_handler.setFormatter(logging.Formatter(
        formatter.replace("${level}", red("FATAL")), datefmt=datefmt))
    logger.addHandler(fatal_handler)

    return logger


__default_logger = None


def get_logger(log_file=None, only_file=False):
    global __default_logger

    if not log_file:
        if not __default_logger:
            dir = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), "..", "logs")
            dir = os.path.abspath(dir)
            if not os.path.exists(dir):
                os.makedirs(dir)
                if not os.path.exists(dir):
                    # The below is not supported in python 2.7
                    # print("make dir %s fail" % dir, file=sys.stderr)
                    sys.stderr.write("make dir %s fail" % dir)
                    os._exit(2)

            _, main_name = os.path.split(sys.argv[0])
            main_name = main_name.replace(".py", "")
            log_file = os.path.join(dir, main_name + ".log")
            __default_logger = __get_logger("default", log_file, only_file)
        return __default_logger
    else:
        return __get_logger(log_file, log_file, only_file)


debug = get_logger().debug
info = get_logger().info
warn = get_logger().warning
err = get_logger().error


def fatal(s):
    global __log_show_stack
    if __log_show_stack:
        s = s + " " + full_stack()
    get_logger().fatal(s)
    sys.exit(1)


if sys.version_info.major == 2 or (sys.version_info.major == 3 and sys.version_info.minor <= 6):
    __this_dir = os.path.dirname(os.path.abspath(__file__))
    if not __this_dir in sys.path:
        sys.path.insert(1, __this_dir)
#   from build_tag import *
# else:
#   from .build_tag import *


def verify_sudo():
    ret = os.system("sudo ls>/dev/null 2>/dev/null")
    if ret != 0:
        err("Can not sudo")
        os._exit(ret_code(ret))


def ret_code(code):
    retcode = code >> 8
    signum = code & 0xff
    if signum != 0:
        return signum
    else:
        return retcode


def cd(dir, show_log=True):
    try:
        if os.path.abspath(os.getcwd()) != os.path.abspath(dir):
            os.chdir(dir)
            if show_log:
                info("cd [" + dir + "]")
    except Exception as e:
        fatal("cd " + dir + " fail: " + str(e))


def get_owner(dir):
    return pwd.getpwuid(os.stat(dir).st_uid).pw_name


def run(cmd, assert_ok=True, show_log=True, raise_exception=False, show_start_log=False, retry_interval=None, retry_timeout=None, retry_times=None):

    if retry_timeout is None and retry_interval is None and retry_times is None:
        return run_impl(cmd, assert_ok, show_log, raise_exception, show_start_log)

    start_time = time.time()
    if retry_timeout is not None and assert_ok:
        fatal("not support")

    if retry_times is not None and assert_ok:
        fatal("not support")

    if retry_times is not None and retry_timeout is not None:
        fatal("not support")

    if retry_timeout is None:
        retry_timeout = 0
    if retry_interval is None:
        retry_interval = 0.5

    if retry_times is None:
        while True:
            try:
                ret = run_impl(cmd, assert_ok, show_log,
                               raise_exception, show_start_log)
                if ret != 0:
                    raise Exception("cmd:%s returns: %s" % (cmd, ret))
            except Exception as ex:
                delta = time.time() - start_time
                if delta < 0 or delta > retry_timeout:
                    err("run %s timeout delta %s timeout %s" %
                        (cmd, delta, retry_timeout))
                    raise ex
                else:
                    info("ignore excpetion ex: %s, sleeping %s ..." %
                         (ex, retry_interval))
                    time.sleep(retry_interval)
                    info("retrying cmd: %s" % cmd)
            return ret
    else:
        for i in range(retry_times):
            try:
                ret = run_impl(cmd, assert_ok, show_log,
                               raise_exception, show_start_log)
                if ret != 0:
                    raise Exception("cmd:%s returns: %s" % (cmd, ret))
                else:
                    return ret
            except Exception as ex:
                info("ignore excpetion ex: %s, sleeping %s ..." %
                     (ex, retry_interval))
                time.sleep(retry_interval)
                info("retrying cmd: %s" % cmd)
                info('this is retry cmd %s times' % (i + 1))
        return ret


def run_impl(cmd, assert_ok=True, show_log=True, raise_exception=False, show_start_log=False):
    global __log_show_stack
    if show_start_log:
        info("start [" + cmd + "] ...")
    ret = os.system(cmd)
    if ret != 0:
        if show_log or assert_ok:

            if assert_ok:
                fail = red("fail")
            else:
                fail = yellow("fail")

            msg = "exec [" + cmd + "] " + fail + \
                " ret:" + str(ret) + " in " + os.getcwd()
            if __log_show_stack:
                msg += " " + full_stack()

            if assert_ok:
                err(msg)
            else:
                warn(msg)

        if raise_exception:
            raise Exception("exec [%s] failed, ret %s" % (cmd, ret))
        if assert_ok:
            os._exit(ret_code(ret))
    else:
        if show_log:
            info("exec [" + cmd + "] " + green("OK"))
    return ret_code(ret)


def _runex(cmd, assert_ok=True, show_log=False, err_output=False, raise_exception=False):
    global __log_show_stack
    try:
        if sys.version_info.major == 2:
            (ret, output) = commands.getstatusoutput(cmd)
        else:
            (ret, output) = subprocess.getstatusoutput(cmd)
    except Exception as e:
        if assert_ok:
            fatal(str(e))
        else:
            ret = 1
            output = str(e)

    if ret != 0:

        if assert_ok:
            fails = red("fail")
        else:
            fails = yellow("fail")
        msg = "exec [" + cmd + "] " + fails + " ret " + \
            str(ret) + " in " + os.getcwd() + " " + output
        if __log_show_stack:
            msg += " " + full_stack()

        if assert_ok:
            err(msg)
            os._exit(ret_code(ret))
        else:
            if show_log:
                warn(msg)
            if not err_output:
                output = ""
        if raise_exception:
            raise Exception("exec [%s] failed" % cmd)
    else:
        if show_log:
            info("exec [" + cmd + "] " + green("OK"))

    return ret, output


def runex3(cmd, **kwargs):
    return _runex(cmd, **kwargs)


def run_cmds(cmds, onfail=None):
    if onfail and not callable(onfail):
        raise TypeError("onfail is not callable")

    ret = 0
    content = ""
    for cmd in cmds:
        ret, content = runex3(cmd, assert_ok=False, show_log=True)
        if ret != 0:
            if onfail:
                onfail()
            err("exec [%s] failed(run_cmds)" % cmd)
            return ret, content
    return ret, content


def run_funcs(funcs, args=None, kwargs=None, onfail=None):
    if onfail and not callable(onfail):
        raise TypeError("onfail is not callable")

    for ix, func in enumerate(funcs):

        if not callable(func):
            raise TypeError("funcs[{index}] is not callable".format(index=ix))

        arg = args[ix] if args else tuple()
        kwarg = kwargs[ix] if kwargs else dict()
        try:
            res = func(*arg, **kwarg)
        except Exception as e:
            err("{func_name} call failed".format(func_name=func.__name__))
            raise e
        if not res:
            if onfail:
                onfail()
            return False
    return True


def runex(cmd, assert_ok=True, show_log=False, err_output=False, raise_exception=False):
    _, output = _runex(cmd, assert_ok=assert_ok, show_log=show_log,
                       err_output=err_output, raise_exception=raise_exception)
    return output


def whoami():
    return runex("whoami")


def log_object(obj):
    info(obj)
    info('  items:' + ', '.join(['%s:%s' %
         item for item in obj.__dict__.items()]))


def is_linux_platform():
    return platform.system().lower() == 'linux'

def is_mac_platform():
    return platform.system().lower() == 'darwin'


def log_platform():
    plat = platform.system().lower()
    if plat == 'windows':
        info('windows system')
    elif plat == 'linux':
        info('linux system')
    elif plat == 'darwin':
        info('mac system')
    else:
        err('unkonw platform : %s' % plat)


def retry(times, interval):
    def decorator(f):
        def wrap(*args, **kwargs):
            for i in range(times):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    time.sleep(interval)
                    warn('Exception: %s, retry time left %s' %
                         (e, times - i - 1))
                    continue
            raise Exception('Retried %s times, mission failed.' % times)
        return wrap
    return decorator


def read_file(name):
    fp = open(name, "r")
    content = fp.read()
    fp.close()
    return content


this_user = ""


def make_dir(dir, sudo=False, show_log=True):
    global this_user
    if not this_user:
        this_user = runex('whoami')

    sudo_cmd = ""
    if sudo:
        sudo_cmd = "sudo "
    if dir == "" or dir == "." or dir == "..":
        return
    if os.path.islink(dir):
        run(sudo_cmd + "rm -f dir", show_log=show_log)
    if not os.path.exists(dir):
        run(sudo_cmd + "mkdir -p " + dir, show_log=show_log)
        if sudo:
            if get_owner(dir) != this_user:
                run("sudo chown -R `whoami`:users " + dir, show_log=show_log)
    else:
        if sudo:
            if get_owner(dir) != this_user:
                run("sudo chown `whoami`:users " + dir, show_log=show_log)
    if not os.path.exists(dir):
        fatal(dir + " not exist")


def write_file(name, content, show_log=True):
    if type(content).__name__ == "bytes":
        content = content.decode('utf-8')
    make_dir(os.path.dirname(name))
    fp = open(name, "w")
    fp.write(content)
    fp.close()
    if show_log:
        info("Write to [%s] OK, size %d" % (name, len(content)))


def dump_json(obj):
    content = json.dumps(obj, indent=2, ensure_ascii=False)
    return content.replace(" \n", "\n")


def load_json(text):
    return json.loads(text, object_pairs_hook=OrderedDict)


def load_json_f(file):
    content = ""
    try:
        content = read_file(file)
    except Exception as e:
        fatal("read from file " + file + " fail: " + str(e))

    try:
        return load_json(content)
    except Exception as e:
        fatal("parse json of file " + file + " fail: " + str(e))


def is_true(text):
    if not text:
        return False
    text = str(text).lower().strip()

    if text.isdigit():
        val = int(text)
        return val != 0
    else:
        return text != "false" and text != "off"


def env_is_true(key):
    return key in os.environ and is_true(os.environ[key])


__dirs = []


def pushd():
    global __dirs
    __dirs.append(os.getcwd())


def popd(show_log=True):
    global __dirs
    dir = __dirs.pop()
    cd(dir, show_log=show_log)


def split_ex(text, ch, func=None):
    lst = []
    tokens = text.split(ch)
    for token in tokens:
        token = token.strip()
        if token:
            if func:
                lst.append(func(token))
            else:
                lst.append(token)
    return lst


def atoi(text):
    ret = 0
    try:
        ret = int(text)
    except Exception as e:
        ret = 0
    return ret


def auto_update(root):
    if not is_linux_platform():
        return False
    me = whoami()
    if me == "osp_jenkins" or me == "admin":
        return
    if "OSP_NO_AUTO_UPDATE" in os.environ:
        return

    pushd()
    #write_file(file, str(now))
    cd(root, show_log=False)
    ret = run("git pull --rebase", assert_ok=False, show_log=True)
    popd(show_log=False)
