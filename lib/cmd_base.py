
from __future__ import print_function
import sys
import os
import getopt
import types

if sys.version_info.major == 2 or (sys.version_info.major == 3 and sys.version_info.minor <= 6):
  __this_dir = os.path.dirname(os.path.abspath(__file__))
  if not __this_dir in sys.path:
    sys.path.insert(1, __this_dir)
  from osp_util import *
else:
  from .osp_util import *

try:
  from enum import Enum, EnumMeta
  enum_module_exists = True
except ImportError as e:
  enum_module_exists = False


if enum_module_exists:

  class Unique(object):
    def __init__(self, cls, *args, **kwargs):
      self._cls = cls
      self._instance = {}

    def __call__(self, value, *args, **kwargs):
      if value not in self._instance:
        self._instance[value] = self._cls(value, *args, **kwargs)
      return self._instance[value]

  @Unique
  class OptionValues(Enum):
    pass

  class OptionDesc(object):
    def _check_values(self, values):
      if not isinstance(values, list):
        raise TypeError("values must is type of list")

    def _init_attrs(self, *args, **kwargs):
      option_name = args[0]
      if isinstance(args[1][0], str):
        self.option = OptionValues(*args)
        self.meta_options = list(self.option)
      elif is_iterable(args[1][0]):
        option_strs = []
        for option_names in args[1]:
          for name in option_names:
            option_strs.append(name)
        self.option = OptionValues(option_name, option_strs)
        self.meta_options = []
        for options_names in args[1]:
          meta_option = []
          for name in option_names:
            meta_option.append(getattr(self.option, name))

          self.meta_options.append(meta_option)
      else:
        raise TypeError("args type is unexpected")

    def __init__(self, *args, **kwargs):

      if isinstance(args[0], str):
        self._init_attrs(*args, **kwargs)
      elif isinstance(args[0], EnumMeta):
        self.option = args[0]
        self.meta_options = args[1]
      else:
        raise TypeError("args type is unexpected")

      self.options = list(self.option)
      self.options_values = [option.name for option in self.options]

    def is_multiple_value(self):
      return is_iterable(self.meta_options[0])

    def get_same_dimension_options(self, option_name):
      cur_option = getattr(self.option, option_name)

      if not self.is_multiple_value():
        return self.options

      for same_dimension_options in self.meta_options:
        if cur_option in same_dimension_options:
          return same_dimension_options

    def get_same_dimension_option_values(self, option_name):
      options = self.get_same_dimension_options(option_name)
      return [option.name for option in options]

  def get_file_system_option():
    return FileSystemOptionDesc.get_option()

  def get_file_flush_option():
    return FileFlushOptionDesc.get_option()

  def get_tag_option():
    return TagOptionDesc.get_option()

  class OptionDescCreator(OptionDesc):
    option = None
    option_name = ''
    meta_info = None

    @classmethod
    def get_option(cls):
      if cls.option is None:
        cls.option = OptionValues(cls.option_name, cls.meta_info)
      return cls.option

    def __init__(self):
      option = self.__class__.get_option()
      options = list(option)

      OptionDesc.__init__(self, option, options)

  class FileSystemOptionDesc(OptionDescCreator):
    option_name = 'file_system'
    meta_info = ('local', 'pangu1', 'pangu2', 'panguLight')

  class FileFlushOptionDesc(OptionDescCreator):
    option_name = 'file_flush'
    meta_info = ('flush', 'cache')

  class TagOptionDesc(OptionDescCreator):
    option = None

    @classmethod
    def get_option(cls):
      if cls.option is None:
        tags_info = get_all_tag_tokens()
        all_tags = []
        for tags in tags_info:
          for tag in tags:
            all_tags.append(tag)
        cls.tag_option = OptionValues('tag', all_tags)
      return cls.tag_option

    def __init__(self):
      option = TagOptionDesc.get_option()
      tags_info = get_all_tag_tokens()
      opt_desc_list = []

      for tags in tags_info:
        opt_desc_item = []
        for tag in tags:
          opt_desc_item.append(getattr(option, tag))
        opt_desc_list.append(tuple(opt_desc_item))

      OptionDesc.__init__(self, option, opt_desc_list)


class TargetDesc(object):
  def __init__(self):
    self.support_target = False

  def get_targets(self, *args, **kwargs):
    return []


class CommandTool(object):
  cmd = ""
  help = ""
  env = {}
  index = {}
  opdesc = []
  enable = True
  self_define = False

  def __check_opdesc(self, cmd, opdesc):
    ch_index = []
    name_index = []
    for op in opdesc:
      ch, name, help, opdefault = op[0:4]
      if ch in ch_index:
        fatal("dupliate [%s] option int %s" % (ch, cmd))
      if name in name_index:
        fatal("dupliate [%s] option int %s" % (name, cmd))

      ch_index.append(ch)
      name_index.append(name)

      if ch == 'h' or name == 'help':
        fatal("-h or --help is used by cmd framework")

  def _init_opdesc(self, opdesc):
    self.opdesc = []
    for op in opdesc:
      if len(op) < 5:
        op_list = list(op)
        op_list.append(None)
        op = tuple(op)
      self.opdesc.append(op)

  def __init__(self, env, cmd, help, opdesc, enable=True, self_define=False, target_desc=TargetDesc()):
    # [optch, opname, ophelp, default_value, option(OptionDesc)]
    opdesc_ = [op[0:4] for op in opdesc]
    self.__check_opdesc(cmd, opdesc_)
    self._init_opdesc(opdesc)

    self.cmd = cmd
    self.target_desc = target_desc
    self.help = help
    self.env = env
    self.index = {}
    self.enable = enable
    self.self_define = self_define
    if not self_define:
      self.opdesc.append(('h', 'help', 'show help', False))

  def optch2opt(self, optch):
    for op in self.opdesc:
      if op[0] == optch:
        return op[1]
    return None

  def build_index(self):
    for op in self.opdesc:
      self.index[op[1]] = op

  def get_targets(self):
    return self.env.args

  def has_opt(self, name):
    return name in self.index

  def get_opt(self, name):
    if not name in self.index:
      fatal("OPTION [" + name + "] does not exist")

    op = self.index[name]
    opdef = op[3]
    name = "--" + name
    if type(opdef) == bool:
      return name in self.env.opts

    if name in self.env.opts:
      return self.env.opts[name]
    return opdef

  def get_optdesc_obj(self, name):
    if not name in self.index:
      fatal("OPTION [" + name + "] does not exist")

    return self.index[name][4]

  def get_opts(self, name):
    if not name in self.index:
      fatal("OPTION [" + name + "] does not exist")

    op = self.index[name]
    opdef = op[3]
    name = "--" + name
    if type(opdef) == bool:
      return [name in self.env.opts]

    if name in self.env.opts_multiple:
      return self.env.opts_multiple[name]
    else:
      return [opdef]


class ExportCmdsTool(CommandTool):
  def __init__(self, env, cmdname, commands='commands'):
    self.commands = commands
    self.cmdname = cmdname
    self.config_file_name = cmdname + '.cmds'
    self.config_dir = '/usr/local/osp-build/hmod/conf'
    self.default_config_file = os.path.join(self.config_dir, self.config_file_name)
    CommandTool.__init__(self, env, "export_cmds", "export or show bash-auto-complete config file", [
        ('s', 'show', 'show content of the config file on screen', False),
        ('c', 'config-file', 'specify bash-completion config file ,default config file is %s' % self.default_config_file, ""),
        ('S', 'shell', 'export bash-completion shell script or not', False),
        ('n', 'cmd-names', 'specify command names(e.g: "hi" or "hi, onebox") when exporting bash-completion shell script,  default command is just "%s"' %
         self.cmdname, self.cmdname, ),
        ('d', 'disable-cover', 'Disable covering existed config file or not', False),
        ('w', 'wordlist', 'accept a incomplete command then return bash-completion wordlist and disable other \'export_cmds\' function', "")
    ])
    self.enable = False

  def get_cmd_configs(self, env):
    content = runex("find " + sys.path[0] + "/%s -type f -name \"*.py\"| awk -F'[/.]' '{print $(NF-1)}'" % self.commands)
    modules = content.splitlines()
    cmd_configs = {}
    for module in modules:
      if module == 'bash':
        continue
      try:
        namespace = {}
        namespace["env"] = env
        exec_code = "import {module}\ncmd = {module}.Tool(env)".format(module=module)
        exec(exec_code, namespace)
        cmd = namespace["cmd"]
        if not cmd.enable:
          continue
        cmd_name = module.split("_tool")[0]
        cmd_configs.update({cmd_name: cmd})
      except Exception as e:
        print("import " + module + red(" FAIL:") + str(e), file=sys.stderr)
        print(full_stack(), file=sys.stderr)
    return cmd_configs

  def output_config_file(self, cmd_configs):
    dst_file = self.get_opt("config-file") if self.get_opt("config-file") else self.default_config_file
    if self.get_opt("disable-cover"):
      dst_file = '.'.join([dst_file, time.strftime("%H%M%S")])
    config = dict()
    for cmd_name, cmd in cmd_configs.items():
      opt_info_dict = dict()
      for op in cmd.opdesc:
        opt_ch = op[0]
        if len(op) >= 5:
          opt_desc_obj = op[4]
          opt_desc_dict = {
              "values": opt_desc_obj.options_values,
              "opt_name": opt_desc_obj.option.__name__
          }
          opt_info_dict.update({opt_ch: opt_desc_dict})
        else:
          opt_info_dict.update({opt_ch: None})
      cmd_info_dict = {'opt': opt_info_dict,
                       'target_desc': cmd.target_desc.__class__.__name__ + '()'}
      config.update({cmd_name: cmd_info_dict})

    config_content = dump_json(config)
    if not self.get_opt("disable-cover") and os.path.exists(dst_file):
      run("rm -f %s" % dst_file)
    write_file(dst_file, config_content)

  def get_cmds(self):
    cmds_str = self.get_opt("cmd-names")
    cmds = cmds_str.split(',')
    return cmds

  def get_word_list(self, env):
    cmd_list = self.get_opt('wordlist').split()
    module = cmd_list[1] + '_tool'
    optch = cmd_list[-2].strip('-')
    cur_choice_str = cmd_list[-1]
    cur_choices = cur_choice_str.split(',')
    namespace = {}
    namespace['env'] = env
    exec_code = 'import {module}\ncmd = {module}.Tool(env)'.format(module=module)
    exec(exec_code, namespace)
    cmd = namespace['cmd']
    cmd.build_index()
    opt = cmd.optch2opt(optch)
    option_desc = cmd.get_optdesc_obj(opt)
    choices = option_desc.options_values

    if option_desc.is_multiple_value():
      cur_words = []
      cur_same_dimension_words = []
      words = []
      for choice in cur_choices:
        if choice in choices:
          cur_words.append(choice)
          same_dimension_words = option_desc.get_same_dimension_option_values(choice)
          cur_same_dimension_words.extend(same_dimension_words)

      cur_same_dimension_words
      for choice in choices:
        if (choice not in cur_choices) and (choice not in cur_same_dimension_words):
          words.append(choice)

      if len(cur_words) > 0:
        cur_words_str = ','.join(cur_words)
        words = [','.join([cur_words_str, word]) for word in words]
      word_list_str = ' '.join(words)
      if cur_choices[-1] in choices:
        word_list_str = cur_choice_str + ' ' + word_list_str
    else:
      word_list_str = ' '.join(choices)

    print(word_list_str)

  def export_shell_script(self):
    cmds = self.get_cmds()
    tpl_script = '/usr/local/osp-build/tpl/bash_auto_complete.in'

    if not os.path.exists(tpl_script):
      fatal("\"bash_auto_complete.in\" not found in <osp-build>(/usr/local/osp-build/tpl)")
      return
    tpl_content = read_file(tpl_script)

    for cmd in cmds:
      content = ""
      config_file_name = cmd + '.cmds'

      cur_content = tpl_content.replace("$CMD_CONFIG_FILE", config_file_name)\
          .replace("$_CMD", "_" + cmd)\
          .replace("$CMD", cmd)\
          .replace("$CONFIG_FILE", "%s_CONFIG_FILE" % cmd.upper())
      content = '\n'.join([content, cur_content])

      dst_dir = os.path.join(sys.path[0], '..', 'conf', 'auto_complete')
      if not os.path.exists(dst_dir):
        dst_dir = os.path.join(sys.path[0], 'conf')
      make_dir(dst_dir)
      dst_file = os.path.join(dst_dir, 'osp_%s.sh' % cmd)
      if os.path.exists(dst_file):
        run("rm -f %s" % dst_file)
      write_file(dst_file, content)

  def main(self):
    env = self.env
    if len(self.get_opt('wordlist')) > 0:
      self.get_word_list(env)
      return 0

    cmd_configs = self.get_cmd_configs(env)
    self.output_config_file(cmd_configs)

    if self.get_opt("shell"):
      self.export_shell_script()

    return 0


def show_opt_help(cmd):
  for op in cmd.opdesc:
    ch, name, help, opdefault = op[0:4]
    text = "    %-20s %s" % ("-" + ch + " --" + name, help.replace("\n", "\n                         "))
    if opdefault:
      text += " [default: %s]" % str(opdefault)
    print(text, file=sys.stderr)


def __show_cmd_help(cmds, key, show_opt):
  cmd = cmds[key]
  if show_opt:
    print("", file=sys.stderr)
  print("  %-20s " % cmd.cmd + cmd.help, file=sys.stderr)
  if show_opt:
    show_opt_help(cmd)


def show_help(env, ver, show_opt=True):
  print(ver, file=sys.stderr)
  print("Usage: " + env.cmdname + " COMMAND [OPTIONS] [TARGETS]", file=sys.stderr)
  print("COMMAND can be:", file=sys.stderr)
  print("  %-20s show all help" % "help", file=sys.stderr)
  print("  %-20s show the detail of the COMMAND" % "help COMMAND", file=sys.stderr)

  cmds = {}
  for cmd in env.cmds:
    if not cmd.enable:
      continue
    cmds[cmd.cmd] = cmd
  lst = sorted(cmds.keys())
  # env.cmd_help_list = ['bar', 'foo'], can show a help command list by user-defined order
  if hasattr(env, "cmd_help_list"):
    for key in env.cmd_help_list:
      if not key in lst:
        fatal(key + " NOT FOUND")
      __show_cmd_help(cmds, key, show_opt)
      lst.remove(key)

  for key in lst:
    __show_cmd_help(cmds, key, show_opt)


def show_cmd_help(env, command, ver):
  print(ver, file=sys.stderr)
  print("Usage: " + env.cmdname + " COMMAND [OPTIONS] [TARGETS]", file=sys.stderr)
  print("COMMAND:", file=sys.stderr)
  for cmd in env.cmds:
    if cmd.cmd == command:
      print("  %-20s %s" % (cmd.cmd, cmd.help), file=sys.stderr)
      show_opt_help(cmd)
      return
    else:
      continue
  print("  Unknown COMMAND" + command, file=sys.stderr)


def get_opt_define(cmd):
  ret = ""
  for op in cmd.opdesc:
    ch, name, help, opdefault = op[0:4]
    if type(opdefault) == bool:
      ret += "-" + ch
    else:
      ret += "-" + ch + ":"
  return ret


def get_long_opt_define(cmd):
  ret = []
  mapping = {}
  for op in cmd.opdesc:
    ch, name, help, opdefault = op[0:4]
    if type(opdefault) == bool:
      ret.append(name)
    else:
      ret.append(name + "=")
    mapping["-" + ch] = "--" + name

  return (ret, mapping)

## __getopt_ex and __getopt_split
# are used to support to find the options in targets
# such as:
# hmod collect .so -f
# python simple getopt.getopt regard the -f as a target, not an option
# use __getopt_ex, we can regard the -f as an option
# if we want to define a target starting with '-'
# use -- , like the linux command
# for example:
# hmod collect .so -f -- -my-files
# -my-files is a target, -f is an option


def __getopt_split(argv):
  argv1 = []
  argv2 = []

  flag = False
  for arg in argv:
    if flag:
      argv2.append(arg)
    else:
      if arg == "--":
        flag = True
      else:
        argv1.append(arg)
  return (argv1, argv2)


def __getopt_ex(argv, short_opts, long_opts):
  ret_opts = []
  ret_args = []
  flag = False
  index = 0

  (argv, argv_targets) = __getopt_split(argv)

  while index < len(argv):
    opts, args = getopt.getopt(argv[index:], short_opts, long_opts)
    ret_opts.extend(opts)
    if flag:
      ret_args.extend(args)
      break
    else:
      found = False
      for arg in args:
        if len(arg) > 0 and arg[0:1] == '-':
          for i in range(index, len(argv)):
            if argv[i] == arg:
              index = i
              found = True
              break
          if found:
            break
          else:
            fatal(arg + " not found in " + str(argv) + " on index " + index)
        else:
          ret_args.append(arg)
      if not found:
        break
  ret_args.extend(argv_targets)
  return (ret_opts, ret_args)


def check_default_not_none(env):
  ok = True
  for op in env.cmd.opdesc:
    ch, name, help, default = op[0:4]
    if not "--" + name in env.opts:
      if default is None:
        err("necessary parameter is missing: -%s --%s %s" % (ch, name, help))
        ok = False
  if not ok:
    sys.exit(1)


def run_tool(env, cmdname, ver, commands="commands"):
  env.cmdname = cmdname

  content = runex("find " + sys.path[0] + "/%s -type f -name \"*.py\"" % commands)
  lines = content.split("\n")

  if enum_module_exists:
    cmd = ExportCmdsTool(env, cmdname, commands)
    cmd.build_index()
    env.cmds.append(cmd)

  for line in lines:
    line = line.strip()
    if not line:
      continue
    pos = line.rfind("/")
    filename = line
    if pos >= 0:
      filename = line[pos + 1:]
    module = filename.replace(".py", "")
    try:
      namespace = {}
      namespace["env"] = env
      exec("import " + module + "\ncmd=" + module + ".Tool(env)", namespace)
      cmd = namespace["cmd"]
      cmd.build_index()
      env.cmds.append(cmd)
    except Exception as e:
      print("import " + module + red(" FAIL:") + str(e), file=sys.stderr)
      print(full_stack(), file=sys.stderr)

  if len(sys.argv) < 2:
    show_help(env, ver, show_opt=False)
    return 1
  if len(sys.argv[1]) <= 0 or sys.argv[1][0:1] == "-":
    show_help(env, ver, show_opt=False)
    return 2
  inputcmd = sys.argv[1]

  if inputcmd == "help":
    if len(sys.argv) >= 3:
      show_cmd_help(env, sys.argv[2], ver)
    else:
      show_help(env, ver)
    return 0

  for cmd in env.cmds:
    if cmd.cmd == inputcmd:
      if cmd.self_define:
        return cmd.main()

      (long_opts, mapping) = get_long_opt_define(cmd)
      opts, args = __getopt_ex(sys.argv[2:], get_opt_define(cmd), long_opts)
      for (opt, _) in opts:
        if opt == "-h" or opt == "--help":
          show_cmd_help(env, cmd.cmd, ver)
          return 1
      optsdict = {}
      optsdict_multiple = {}
      # mapping {'-d' : 'depth'}
      for (name, val) in opts:
        if name in mapping:
          name = mapping[name]
        optsdict[name] = val
        if not name in optsdict_multiple:
          optsdict_multiple[name] = []
        optsdict_multiple[name].append(val)
      env.opts = optsdict
      env.opts_multiple = optsdict_multiple
      env.args = args
      env.cmd = cmd
      check_default_not_none(env)
      return cmd.main()
  fatal("Unknown COMMAND: " + inputcmd)
