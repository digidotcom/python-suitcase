## Suitcase Change Log

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
