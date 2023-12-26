
import unittest
import os
import os.path

from collections import OrderedDict
from contextlib import contextmanager

from argparse import Namespace
import subprocess as sp

from lbstanza_wrappers.Lbstanza import FuncDeclExporter

@contextmanager
def open_test(fpath):
  uutDir = os.path.dirname(fpath)
  if not os.path.isdir(uutDir):
    os.makedirs(uutDir)

  with open(fpath, "w") as f:
    yield f

basic_funcs = OrderedDict()
basic_funcs["basic_some_func"] = (
  {
    "a": ("int", 0, "int"),
    "b" : ("char", 1, "ptr<byte>"),
  },
  ("int", False, ""),
  "" # Not Used
)


class TestFuncDeclExporter(unittest.TestCase):
  def test_basic(self):
    """
    """
    stanza_dir = "tests/uut/func_exporter/"
    fout = os.path.join(stanza_dir, "basic.stanza")
    with open_test(fout) as cap:

      exp = FuncDeclExporter(cap)
      opts = Namespace(pkg_prefix="wrapper/func_exporter", pkg_name = "basic")
      exp.dump_func_decls(basic_funcs, opts)

    sp.check_call("stanza build test_func_exporter", cwd="./tests", shell=True)
    sp.check_call(["tests/bin/test_func_exporter"], shell=True)


