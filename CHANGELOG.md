## Suitcase Change Log

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

### 0.6 / 2016-06-24

* Initial Public release of the library
