import unittest
import os
import os.path
from argparse import Namespace
import subprocess as sp

from pycparser import parse_file
import pycparser_fake_libc


from lbstanza_wrappers.FuncDeclVisitor import FuncDeclVisitor

from .utils import open_test


class FuncDeclVisitorTests(unittest.TestCase):
  def test_basic(self):

    stanza_dir = "tests/uut/func_visitor/"
    fout = os.path.join(stanza_dir, "standard-externs.stanza")
    with open_test(fout) as cap:

      opts = Namespace(
        output = cap,
        dump_types = False,
        dry_run = False,
        pkg_prefix="wrapper/func_visitor",
        pkg_name="standard-externs"
        )

      cpp_args = ""
      node = parse_file("tests/stanza/standard_externs.h", use_cpp=True, cpp_args=cpp_args)
      visitor = FuncDeclVisitor(opts)
      visitor.visit(node)
      visitor.export()

    sp.check_call("stanza build test_func_visitor", cwd="./tests", shell=True)
    sp.check_call(["tests/bin/test_func_visitor"], shell=True)









