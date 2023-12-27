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

# Tests

There is a unit test suite that will attempt to use the python script
to extract C header content into `stanza` code and then run the `stanza` compile
on the resultant code. These tests cover the full loop from C header to running
stanza code.

## Setup

You will need the `stanza` compiler on your PATH. [Download here](https://lbstanza.org/downloads.html). Use
version 0.18.10 or higher. Check you are setup correctly with `stanza version`

You will need to setup the python venv as described above.

I ran into a funny issue where if I put my `.stanza` config in the root directory, it would not
build the stanza test project because it would look for `stanza.proj` in the root. I instead
put it in `tests/.stanza` and then this worked fine. If you have your `.stanza` in `$HOME` this
may be a non-issue.

## Running the Tests:

```
$> ./run_tests.sh
Build target test_enum_exporter is already up-to-date.
[Test 1] test_basic
[PASS]

[Test 2] test_non_zero
[PASS]

[Test 3] test_negative
[PASS]

Tests Finished: 3/3 tests passed. 0 tests skipped. 0 tests failed.

Longest Running Tests:
[PASS] test_basic (58 us)
[PASS] test_negative (12 us)
[PASS] test_non_zero (11 us)
.Build target test_native_enum_exporter is already up-to-date.
[Test 1] test_native_exporter
[PASS]

Tests Finished: 1/1 tests passed. 0 tests skipped. 0 tests failed.

Longest Running Tests:
[PASS] test_native_exporter (61 us)
.Build target test_func_exporter is already up-to-date.
[Test 1] test_basic
[PASS]

Tests Finished: 1/1 tests passed. 0 tests skipped. 0 tests failed.

Longest Running Tests:
[PASS] test_basic (8 us)
.[Test 1] test_standard_externs
[PASS]

[Test 2] test_standard_externs_void
[PASS]

[Test 3] test_standard_externs_multi_args
[PASS]

[Test 4] test_standard_externs_off_sigs
[PASS]

[Test 5] test_standard_externs_structs_test1
[PASS]

[Test 6] test_standard_externs_func_ptr
[PASS]

Tests Finished: 6/6 tests passed. 0 tests skipped. 0 tests failed.

Longest Running Tests:
[PASS] test_standard_externs (67 us)
[PASS] test_standard_externs_void (9 us)
[PASS] test_standard_externs_multi_args (9 us)
[PASS] test_standard_externs_off_sigs (6 us)
[PASS] test_standard_externs_func_ptr (3 us)
[PASS] test_standard_externs_structs_test1 (2 us)
.
----------------------------------------------------------------------
Ran 4 tests in 4.440s

OK
```
