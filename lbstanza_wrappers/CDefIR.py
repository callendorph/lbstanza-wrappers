from dataclasses import dataclass
from typing import OrderedDict

from pycparser import c_ast

class ToStanzable:
  """ Base class for Stanzable Definitions
    All inheritors must implement `to_stanza`
  """
  def to_stanza(self):
    raise NotImplementedError("This class Failed to implement to stanza")

@dataclass
class Identifier(ToStanzable):
  """ Identifier describes named symbols like 'int', 'char', etc.
  """
  name:str

  def to_stanza(self):
    return self.name

@dataclass
class EnumArg(ToStanzable):
  """ Defines an Enum Argument that is typically used in
  place of an Identifier
  """
  enumVals:list[str]

  def to_stanza(self):
    # We replace enums with int to satisfy the C calling
    # interface.
    return "int"

@dataclass
class StructArg(ToStanzable):
  """ Defines an Struct Argument that is typically used in
  place of an Identifier
  """
  members:list[str]

  def to_stanza(self):
    # We replace enums with int to satisfy the C calling
    # interface.
    return "struct"

@dataclass
class ArgType(ToStanzable):
  """ The ArgType encapsulates type and the number of pointers
  to that type.
  This typically unpacks into something like `int` for no
  pointers or  `ptr<int>` for 1 pointer.
  Example: Void or struct pointers unpack to `ptr<?>`
  """
  lbType:ToStanzable
  numPtrs:int

  def to_stanza(self) -> str:
    if self.numPtrs > 0 :
      return self.to_ptr_str()
    else:
      return self.arg_to_stanza()

  def arg_to_stanza(self):
    return self.lbType.to_stanza()

  FIXED_PTR_MAPPING = {
    "char" : "byte",
    "void" : "?",
    # This only affects pointers to structures
    #   if it is a struct by value - then we
    #   have to handle it a different way.
    "struct" : "?",
    # TODO - I think this needs to be removed
    #  with the new structure for FunctionData
    #  which can generate with `to_stanza`
    "funcdef" : "?",
    "int-enum" : "int"
  }

  def to_ptr_str(self):
    baseType = self.arg_to_stanza()
    ptrType = self.FIXED_PTR_MAPPING.get(baseType, baseType)
    prefix = "ptr<" * self.numPtrs
    suffix = ">" * self.numPtrs
    return prefix + ptrType + suffix

@dataclass
class ReturnType(ToStanzable):
  """ Captures the Return Type from a Function
  This basically consists of an ArgType and a
  flag to indicate whether the return is `void` or not
  LoStanza doesn't handle `void` - it just expects everything
  to be converted to `int`
  """
  retType:ArgType
  isVoid:bool

  def to_stanza(self) -> str:
    return self.retType.to_stanza()

@dataclass
class FunctionData(ToStanzable):
  """ Function Declaration Data Type
  This encapsulates the args and return type that are used
  to generate the stanza code that wraps a C declaration.
  """
  args:OrderedDict[str, ArgType]
  ret:ReturnType
  fdef:c_ast.Node

  def to_stanza(self) -> str:
    argStr = ",".join([v.to_stanza() for _,v in self.args.items()])
    ret = "(({}) -> {})".format(argStr, self.ret.to_stanza())
    return ret