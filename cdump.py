from pycparser import parse_file, c_parser, c_ast
import argparse

def setup_opts() :
  desc = """ Helper tool to dump the C AST from a particular file. This can help
  debug transformations of C to other languages.
  """
  parser = argparse.ArgumentParser(description=desc)
  inputHelp = (
    "Path to a file that will be parsed for function declarations. "
    "It is useful to strip the file using the preprocessor "
    "before passing this file to pycparser. "
    "Use 'gcc -E -std=c99' for example."
  )
  parser.add_argument("-i", "--input", type=str, help=inputHelp)
  opts = parser.parse_args()
  return opts


if __name__ == "__main__":
  opts = setup_opts()
  ast = parse_file(filename=opts.input)
  ast.show(showcoord=True)
