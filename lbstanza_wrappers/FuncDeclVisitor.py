import logging
import sys
from collections import OrderedDict
from pycparser import c_ast

from lbstanza_wrappers.Lbstanza import FuncDeclExporter, LBStanzaExporter
from lbstanza_wrappers.CDefIR import *

class FuncDeclVisitor(c_ast.NodeVisitor):
  """ Extract the Type Declarations into an Intermediate store.
  This class is intended to be a first pass for extracting function
  declarations. The idea is to just extract the
  """
  # NOTE - the pycparser fake headers don't handle
  #   conversion of stdint.h types well, so I'm
  #   implementing a better mapping here.
  #
  #   The keys in this mapping are standard C type definitions.
  #   The values in this mapping should all be lbstanza primitives.
  #     The exceptions to this is for struct definitions (not struct ptrs, they are ptr<?>)
  #        and function pointer typedefs (not declarations).
  #     The struct definitions will use 'struct' as keyword. This is necessary because
  #        currently lbstanza doesn't handle passing struct by value.
  #     The function pointers will use 'funcdef'. This will make reference to the
  #        `self._funcdef` dict that will contain more info about that particular
  #        function pointer.
  FIXED_TYPE_MAPPING = {
    "double" : "double",
    "float" : "float",
    "int" : "int",
    "unsigned" : "int",
    "signed" : "int",
    "long" : "long",
    "char" : "byte",
    "void" : "void",
    "bool" : "byte", #  <-- GCC uses byte for this
    "Bool" : "int",
    "_Bool" : "int",
    "uint" : "int",
    "ulong" : "long",
    "uint32_t" : "int",
    "int32_t" : "int",
    "uint64_t" : "long",
    "int64_t" : "long",
    # What to do with `short` and `ushort` ?
    "short" : "int",
    "ushort" : "int",

    "long int" : "long",
    "short int" : "int",
    # Stanza Doesn't really differentiate
    "unsigned int" : "int",
    "signed int" : "int",
    "unsigned long" : "long",
    "signed long" : "long",
    "unsigned char" : "byte",
    "signed char" : "byte",
    "unsigned short" : "int",
    "signed short" : "int",
    # TODO - This is a bug - "long long" and "long" are not the same
    "long long" : "long"
  }

  def __init__(self, opts):
    self._opts = opts
    super().__init__()

    self._types = self._init_types()
    self._funcs = OrderedDict()
    self.logger = None
    self.rootNode = None

  def _init_types(self):
    ret = {}
    for k,v in self.FIXED_TYPE_MAPPING.items():
      ret[k] = Identifier(v)
    return ret

  def debug(self, msg):
    if self.rootNode is not None:
      logging.debug("{}: {}".format(self.rootNode.coord, msg))
    else:
      logging.debug("UNKNOWN: {}".format(msg))

  @property
  def types(self):
      return self._type

  @property
  def func_defs(self):
    for name, t in self._type.items():
      if isinstance(t, FunctionData):
        yield name

  @property
  def enum_defs(self):
    for name,t in self._type.items():
      if isinstance(t, EnumArg):
        yield name

  @property
  def struct_defs(self):
    for name, t in self._type.items():
      if isinstance(t, StructArg):
        yield name

  def visit_Typedef(self, node):
    # We use this to capture the type declarations and
    #  Store a mapping of how translate these from C to Stanza
    #  Stanza has only a handful of types and so there is a need to
    #  handle conversion properly.
    self.rootNode = node
    comps = self.capture_typedef(node)
    if comps is not None:
      name, lbType, *_ = comps

      existing = self._types.get(name)
      if existing is not None:
        self.debug("Type named '{}' Already Exists - Ignoring new definition".format(name))
        return

      self._types[name] = lbType

  def visit_Decl(self, node):
    self.rootNode = node
    numPtrs = 0
    if type(node.type) is c_ast.FuncDecl:
      if node.name in self._funcs:
        logging.info("{}: Ignoring Existing Function Decl: {}".format(node.coord, node.name))
        return
      fdef = node.type
      funcData = self.capture_funcdecl(fdef)
      self._funcs[node.name] = funcData
      logging.debug("{}: Captured Function Decl: {}".format(node.coord, node.name))
    elif type(node.type) is c_ast.Struct:
      declname = node.type.name
      if declname in self._types:
        self.debug("Type with name '{}' Already Exists - Ignoring New Struct Declaration".format(declname))
        return
      # @TODO - capture struct members here ?
      lbType = ArgType(StructArg({}), 0)
      self._types[declname] = lbType
      self.debug("Captured Struct Decl '{}' as Dummy Definition".format(declname))
    else:
      self.debug("Unhandled Type: {}" % [type(node.type)])

  def capture_typedef(self, node):
    """ Traverse the node tree to determine the type of
    declaration is expressed by this node.
    This compresses pointer types into a number of levels
      of redirection.
    """
    param = node
    numPtrs = 0
    while True:
      if type(param.type) is c_ast.TypeDecl:
        baseNode = param.type.type
        if type(baseNode) is c_ast.Struct:
          return self.capture_struct(baseNode, numPtrs, param.type.declname)
        elif type(baseNode) is c_ast.IdentifierType:
          return self.capture_identifier(baseNode, numPtrs, param.type.declname)
        elif type(baseNode) is c_ast.Enum:
          return self.capture_enum_typedef(baseNode, param.type.declname)
        elif type(baseNode) is c_ast.Union:
          self.debug("Ignoring Typedef of Base Union: {}".format(baseNode))
        else:
          raise RuntimeError("{}: Unhandled declaration base: {}".format(self.rootNode.coord, baseNode))
      elif type(param.type) in [c_ast.PtrDecl, c_ast.ArrayDecl]:
        numPtrs += 1
        param = param.type
      elif type(param.type) is c_ast.IdentifierType:
        # No op - I don't think this make sense for a typedef
        #  - Is this an alias - like:
        #    typedef asdf qwer
        raise RuntimeError("{}: Unhandled Identifier Type: {}".format(node.coord, node))
      elif type(param.type) is c_ast.FuncDecl:
        return self.capture_funcdef(node, numPtrs, param.type)
      else:
        raise RuntimeError("{}: Unhandled Node in Declaration: {}".format(node.coord, node))

  def capture_struct(self, node, numPtrs, declname):
    # Currently, I'm not capturing the struct parameters because we
    #  don't actually use them in the wrapper generator. We generally
    #  assumes structs are opaque types.
    structContent = {}
    lbType = ArgType(StructArg(structContent), numPtrs)
    self.debug("Captured Struct: {} = {}".format(declname, lbType))
    return (declname, lbType)

  def capture_identifier(self, node, numPtrs, declname):
    baseType = " ".join(node.names[-2:])
    # Attempt to convert to lbtype - and if that
    #  doesn't work return the baseType - we will
    #  attempt a lookup later.
    aliasType = self._types.get(baseType)
    if aliasType is None:
      # This type is referencing a type we don't know about yet - that
      # is a little strange.
      raise RuntimeError("{}: Unhandled declaration base: {}".format(self.rootNode.coord, node))

    lbType = ArgType(aliasType, numPtrs)

    self.debug("Captured Identifier: {} = {}".format(declname, lbType))

    return (declname, lbType)

  def capture_enum_typedef(self, node, declname):
    """
    @param baseNode enumeration node - a child/grand-child of the rootNode
    @param declname Name of the enumeration that we are trying to capture.df
    """
    self.debug("Captured Enum: {}".format(declname))
    # @TODO implement Enum List Capture -
    #  This may or may not be possible - the _enum might be defined elsewhere ?
    enumVals = []
    return (declname, EnumArg(enumVals))

  def capture_funcdecl(self, fdef):
    # Now we need to extract the function declaration - parameters and
    #   return arguments.
    args = self.get_args(fdef)
    retType = self.get_retType(fdef)

    return FunctionData(args, retType, fdef)

  def capture_funcdef(self, node, numPtrs, fdef):
    """ Capture a Function Pointer Definition
    @param node
    """
    name = node.name
    data = self.capture_funcdecl(fdef)

    if numPtrs == 0:
      # Z3 uses funny function pointer declarations. It is
      #  almost as if the function is passed by value instead
      #  of by pointer. See `Z3_set_error_handler`
      #  This a hack to make this work with Stanza's expectation
      #  of how to pass a function pointer.
      numPtrs += 1

    lbType = ArgType(data, numPtrs)

    self.debug("Captured FuncDef: {} NumPtrs: {}".format(name, numPtrs))
    return (name, lbType)

  def fix_arg_name(self, name, argMap):
    """ Stanza has some keywords that can't be used as variable names
      like `val`, `when`, etc. This function inspects the name of an
      argument and then constructs a new variable name that doesn't collide
      with stanza reserved words.
    @param name of the argument or declaration
    @param argMap Existing re-mapped arguments - to check that we don't
      create an overlap.
    @return [String] new name
    """
    if name is not None and name not in LBStanzaExporter.RESERVED_WORDS:
      return name

    if name is None:
      name = "missing_name"

    newName = name + "_v"
    i = 1
    while newName in argMap.keys():
      newName = name + "_v{}".format(i)
      i += 1
    return newName

  def get_args(self, n):
    """ Extract the arguments from a function definition.
    The function arguments are encoded in a `ParamList` object - See here:
      https://github.com/eliben/pycparser/blob/f7409953060f1f4d0f8988f1e131a49f84c95eba/pycparser/c_ast.py#L831
    @param n Func Declaration Node that we are attempting to parse
    @return OrderedDict of:
      Key => Name of the argument
      Value = Tuple of (lbType, numPtrs, completeType) where:
        lbType => Base stanza type extracted from the C type
        numPtrs => Number of * pointers in the declaration
        completeType => Fully formatted type including any `ptr<>`
          decorators.
    """
    ret = OrderedDict()
    if n.args is None:
      return ret
    for p in n.args.params:
      name, argType = self.get_decl(p)

      if argType.lbType.to_stanza() == "void" and argType.numPtrs == 0:
        # C functions with signature `int somefunc(void)` don't have any
        #  arguments so we just skip this.
        continue

      name = self.fix_arg_name(name, ret)

      ret[name] = argType

    return ret

  def get_retType(self, n):
    """ Get the return type for function definition
    @param n Function Declaration Node
    """
    name, lbType = self.get_decl(n)
    isVoid = False
    if lbType.to_stanza() == "void" and lbType.numPtrs == 0:
      # Stanza can't handle void return - it has to be
      #  int
      lbType = Identifier("int")
      isVoid = True

    return ReturnType(lbType, isVoid)

  def get_decl(self, param):
    """ Extract a declaration type from one of the args to a C function.
    This function is about extracting the type declarations we have
    already captured and presenting them for use by a function
    def or declaration.
    @param param
    @return tuple of Name, Stanzable
    """
    p = param
    numPtrs = 0
    while True:
      if type(p.type) is c_ast.TypeDecl:
        baseNode = p.type.type
        try:
          baseType = baseNode.name
        except AttributeError:
          baseType = " ".join(baseNode.names[-2:])

        lbType = self._types.get(baseType)
        if lbType is None:
          raise ValueError("Failed to Find Type Mapping for TypeDecl '{}'".format(baseType))

        return (p.type.declname, ArgType(lbType, numPtrs))
      elif type(p.type) in [c_ast.PtrDecl, c_ast.ArrayDecl]:
        numPtrs += 1
        p = p.type
      elif type(p.type) is c_ast.IdentifierType:
        baseType = p.type.names[-1]
        lbType = self._types.get(baseType)
        if lbType is None:
          raise ValueError("{}: Failed to Find Type Mapping for Identifier '{}'".format(self.rootNode.coord, baseType))
        # @NOTE - this is primarily for parsing functions
        #   that return void.
        return ("", ArgType(lbType, numPtrs))
        #return "void", "int", 0
      elif type(p.type) is c_ast.FuncDecl:
        return self.capture_funcdef(param, numPtrs, p.type)
      else:
        raise RuntimeError("{}: Unhandled Decl Type: {}".format(param.coord, p))


  def dump_types(self):
    from pprint import pprint
    print("Enums:")
    pprint(list(self.enum_defs))
    print("Types:")
    pprint(self._types)
    print("FuncDefs:")
    fNames = list(self.func_defs)
    pprint(fNames)
    print("Funcs:")
    fNames = list(self._funcs.keys())
    pprint(fNames)

  def export(self):
    """ Generate the exported stanza wrapper file for the
    captured header.
    """
    if self._opts.dump_types:
      self.dump_types()

    if self._opts.dry_run:
      fout = sys.stdout
    else:
      if isinstance(self._opts.output, str):
        fout = open(self._opts.output, "w")
      else:
        # Unit Tests pass a File object directly
        #  so that we can more easily output the result
        #  to the desired location or a string buffer.
        fout = self._opts.output

    exp = FuncDeclExporter(fout)
    exp.dump_func_decls(self._funcs, self._opts)
