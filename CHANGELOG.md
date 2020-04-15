## Suitcase Change Log

### 0.12 / 2020-04-15

[Full Changelog](https://github.com/digidotcom/python-suitcase/compare/0.11...0.12)

Enhancements:

* Added support for non-greedy DispatchTargets, so that such fields can be
  appear in a structure before a greedy field (e.g. Payload) without error.

Bugfixes:

* Previously, `DependentField` would not work if it appeared within a
  `SubstructureField` or a `FieldArray`. This has been corrected.
* Updated the `unpack` method of fields and structures to ensure consistent
  return types. Previously, some fields would return None while others would
  return the unused data; now fields should always return non-None.

### 0.11 / 2019-03-25

[Full Changelog](https://github.com/digidotcom/python-suitcase/compare/0.10...0.11)

Enhancements:

* [Added 32-bit and 64-bit float fields][pr-46]
* [Added support for DispatchTarget over a BitField field][pr-54]

Other Changes:

* [Testing support for Python 3.3, 3.4 and PyPy 2.7 has been dropped][pr-53]

[pr-46]: https://github.com/digidotcom/python-suitcase/pull/46
[pr-54]: https://github.com/digidotcom/python-suitcase/pull/54
[pr-53]: https://github.com/digidotcom/python-suitcase/pull/53

### 0.10 / 2016-10-2016

[Full Changelog](https://github.com/digidotcom/python-suitcase/compare/0.9...0.10)

Bugfixes:

* [Fixed 0-length Field Arrays](https://github.com/digidotcom/python-suitcase/issues/24)

Enhancements:

* Supported was added for conditional SubstructureFields
* On error, original stack trace is now saved properly
* FieldArrays size can be specified in terms of number of elements
  instead of a length provider (in bytes).
* `dir()` method now works as expected on Field instances
* Fields may now be constructed by providing keyword arguments to
  the constructor.  This eliminates the need to assign each field
  explicitly.

Other Changes:

* Python 3.2 support has been dropped

### 0.9 / 2015-11-12
[Full Changelog](https://github.com/digidotcom/python-suitcase/compare/0.8...0.9)

Bug Fixes:

* Fixed error message when building exception in TypeField
* Miscellaneous documentation fixes
* `ConditionalField` now properly works with empty fields without
  acting like those fields are not present at all.

Enhancements:

* Python 3.5 is now officially supported as is pypy 4.0.0
* You can now specifies functions that customize how get/set works on
  `LengthField`.  This allows for things like having the field that
  provides length to be within a `BitField`.

### 0.8 / 2015-10-02
[Full Changelog](https://github.com/digidotcom/python-suitcase/compare/0.7...0.8)

Bug Fixes:

* Fixed inconsistencies getting length from LengthProvider
* Fixed potential problems when discarding bytes when throwing away
  bytes from a StreamProtocolHandler looking for a Magic field

Enhancements:

* Support for LengthFields and Payloads in ConditionalFields added
* Support added for 24, 40, 48, and 56 bit integers
* Support added for an array of substructures via `FieldArray`
* `TypeField` added for supporting field providing length based on type.
* `SubstructureField` added allowing for individuals fields with
  multiple elements to be modeled as structures.

### 0.7 / 2015-07-29
[Full Changelog](https://github.com/digidotcom/python-suitcase/compare/0.6...0.7)

Bug Fixes:

* Several documentation fixes
* [#3](https://github.com/digidotcom/python-suitcase/issues/3):
  Added dependencies for the package to setup.py
* [#5](https://github.com/digidotcom/python-suitcase/issues/5): Fixed
  `__repr__` for `FieldProperty` and other Fields that do not override
  that method and also do not use `_value`.

Enhancements:

* [#7](https://github.com/digidotcom/python-suitcase/issues/7):
  Support for a `DispatchTarget` of None is now supported.  This
  allows for the target to be dynamically sized (greedy) which enables
  several previously impossible use cases that show up frequently in
  practice.

### 0.6 / 2015-06-24

* Initial Public release of the library
