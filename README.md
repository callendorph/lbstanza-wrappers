# LBStanza C-Wrapper Tools

This project contains some python tools for making wrappers around C libraries in stanza. The idea is to convert the C syntax into something that stanza can read and process.

These tools are based on [pycparser](https://github.com/eliben/pycparser).

## Setup

```
sudo apt install python3-venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Examples

Extract an Enumerated Type in C:

Example Header: [libtidy](https://github.com/htacg/tidy-html5/blob/a873a190e10227c47c675b8c89e6619659784db9/include/tidyenum.h#L692)

```c
/** A Tidy configuration option can have one of these data types. */
typedef enum
{
  TidyString,          /**< String */
  TidyInteger,         /**< Integer or enumeration */
  TidyBoolean          /**< Boolean */
} TidyOptionType;

```

First pass this though the C PREPROCESSOR so that we get rid of
symbols and things that the `pycparser` can't handle:

```
gcc -E -std=c99 ./tidy-html5/include/tidyenum.h > header.h
```

Then we can run the tool:
```
convert2stanza.py --input header.h enums --out-dir ./temp --pkg-prefix "tidy/Enums"
```

This will create a file `./temp/TidyOptionType.stanza` (among others) containing:

```
defpackage tidy/Enums/TidyOptionType :
  import core

public deftype TidyOptionType
public deftype TidyString <: TidyOptionType
public deftype TidyInteger <: TidyOptionType
public deftype TidyBoolean <: TidyOptionType

public defn to-int (v:TidyOptionType) -> Int:
  match(v) :
    (x:TidyString) : 0
    (x:TidyInteger) : 1
    (x:TidyBoolean) : 2

public defn TidyOptionType (v:Int) -> TidyOptionType :
  switch {v == _}:
    0 : new TidyString
    1 : new TidyInteger
    2 : new TidyBoolean
    else: throw(Exception("Invalid Exception Value"))

public lostanza defn TidyOptionType (v:int) -> ref<TidyOptionType> :
  return TidyOptionType(new Int{v})

defmethod print (o:OutputStream, v:TidyOptionType) :
  match(v) :
    (x:TidyString) : print(o, "TidyString")
    (x:TidyInteger) : print(o, "TidyInteger")
    (x:TidyBoolean) : print(o, "TidyBoolean")
```

See [lbstanza-tidy](https://github.com/callendorph/lbstanza-tidy)
