Pacman
------

Overview
========
Pacman is a library providing a set of primitives and helpers for
specifying and parsing protocols.  The library seeks to adhere to
these core principles:

*Simple Interfaces*
  Interfaces to the library should be simple and there should be a
  logical consistency in the library API.  Internally, advanced
  language techniques are used, but the API consumer shouldn't need to
  be aware of these details.

*Declarative Syntax*
  Wherever appropriate, the library should seek to provide a syntax
  for specifying protocols that is as declarative as possible.  These
  declarations should be explicit and it should be clear what is being
  declared.

*Informative Error Messages*
  When implementing a protocol, you usally don't get it right the
  first time.  The library should use all available inforamtion to
  provide information to the API consumer that can help them figure
  out what is going wrong easily.

*Common Use Cases Should Be Easy*
  There are certain data types/patterns that are common amogst
  protocols.  The library should include code to help with these cases
  to make the programmer's life easier.

*Less Common Use Cases Should Be Possible*
  When there is a protocol that is significantly different than the
  norm, the library should still provide some useful code that can be
  reused.  Some parts of the library might need to be abondoned, but
  the hope would be that one would not need to start from scratch.
