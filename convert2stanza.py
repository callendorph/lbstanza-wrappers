#!/usr/bin/env python3
import argparse
import os
import pkg_resources

from pycparser import parse_file
import pycparser_fake_libc

from lbstanza_wrappers.EnumVisitor import EnumVisitor
from lbstanza_wrappers.FuncDeclVisitor import FuncDeclVisitor

__version__ = pkg_resources.require("lbstanza-wrappers")[0].version

import logging
logging.basicConfig(
  level=os.environ.get('PY_LOGLEVEL', 'INFO').upper()
)


def prep_args(opts):
  def to_header(fpath):
    return "-I" + fpath
  fake_libc_arg = to_header(pycparser_fake_libc.directory)
  others = [to_header(x) for x in opts.include]
  cpp_arg_list = others + [fake_libc_arg]
  cpp_args = " ".join(cpp_arg_list)
  return cpp_args

def process_func_decl(opts):
  cpp_args = prep_args(opts)
  node = parse_file(opts.input, use_cpp=True, cpp_args=cpp_args)
  v = FuncDeclVisitor(opts)
  v.visit(node)
  v.export()

def process_enums(opts):
  cpp_args = prep_args(opts)
  node = parse_file(opts.input, use_cpp=True, cpp_args=cpp_args)
  v = EnumVisitor(opts)
  v.visit(node)

def setup_opts():
  desc = """
  LBStanza C Wrapper Generator

  This tool is used to generate wrappers around a C library (static or dynamic).

  This tool uses 'pycparser'. As such, you should follow instructions defined in
  that project for using the C preprocessor to message headers before feeding them
  to this tool (eg, 'gcc -E -std=c99 headers.h' ).

  Function Declaration Generator
  ------------------------------

  This sub-command will generate all the exported C function declarations
  as stanza external declarartions.

  1.  First it Generates the static extern definitions, eg
     extern some_func : (int, int) -> int
  2.  Then it dumps wrappers that handle the `call-c` invokation, eg
     public lostanza defn w_some_func(i:int, j:int) -> int :
       val ret = call-c some_func(i, j)
       return ret

  As of lbstanza version v0.18.10, the compiler can figure out
  the difference between static and dynamic compiling on its own. This
  means it no longer needs the compile-time flag hack previous
  versions of this tool used.

  Enum Generator
  --------------
  This sub-command will generate a stanza Enum definition for each
  C-enum declaration.

  For well-formed C-enums - this code will use the `defenum` construct
  in stanza. "Well-Formed" in this context means values start at zero and
  increase monotonically without gaps.
  For non-"Well-Formed" C-enums, this will generate a backup implementation
  that is not as pretty or performant.

  Logging
  -------

  You can set the environment variable "PY_LOGLEVEL" to a string to control
  the logging level. Example:

  PY_LOGLEVEL=DEBUG convert2stanza.py ...

  """
  parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("-i", "--input", type=str, help="Path to the header file that will be parsed for function declarations")
  parser.add_argument("-I", "--include", action="append", default=[], help="Add an additional search path for headers. This arg can be used multiple times.")

  sub = parser.add_subparsers(help="Extraction Operations")

  ep = sub.add_parser("enums", help="Extract Enumerated Types into a Stanza Style")
  ep.add_argument("--pkg-prefix", help="Prefix string when declaring the 'defpackage'")
  ep.add_argument("--out-dir", help="Directory where stanza files will be created.")
  ep.add_argument("--dry-run", action="store_true", help="Generate all output to stdout instead of files in the `--out-dir`.")
  ep.add_argument("--use-defenum", action="store_true", help="Generate defenum structures for all well-formed C enums.")
  ep.add_argument("--skip", action="append", default=[], help="Don't generate any enumeration files for objects whose name matches the passed string. This argument can be used multiple times.")
  ep.set_defaults(func=process_enums)

  fp = sub.add_parser("func-decl", help="Extract Function Declarations into a Stanza Style")
  fp.add_argument("--pkg-prefix", help="Prefix string when declaring the 'defpackage'")
  fp.add_argument("--pkg-name", default="Wrapper", help="Name of the package containing the func decl. Default is '%(default)s'")
  fp.add_argument("--output", help="Output file that will contain the wrapper declarations")
  fp.add_argument("--func-form", required=True, choices=['static', 'dynamic', 'both'], help="Select which form of function declaration output to generate.")
  fp.add_argument("--dry-run", action="store_true", help="Generate all output to stdout instead of to file.")
  fp.add_argument("--dump-types", action="store_true", help="Dump the captured types, enums, structs, and functions to stdout.")
  fp.set_defaults(func=process_func_decl)

  opts = parser.parse_args()
  return opts

def main():
  opts = setup_opts()
  opts.func(opts)

if __name__ == "__main__":
    main()
