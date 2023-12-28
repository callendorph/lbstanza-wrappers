
import unittest
import os
import os.path

from collections import OrderedDict
from contextlib import contextmanager

from argparse import Namespace
import subprocess as sp

from lbstanza_wrappers.Lbstanza import *
from lbstanza_wrappers.CDefIR import *

from .utils import open_test

basic_funcs = OrderedDict()
basic_funcs["basic_some_func"] = FunctionData(
  OrderedDict({
    "a": ArgType(Identifier("int"), 0),
    "b" : ArgType(Identifier("char"), 1),
  }),
  ReturnType(ArgType(Identifier("int"), 0), False),
  None
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


