
LuaAutocomplete
===============

This is a very basic auto-completion plugin for Sublime Text 3 and the Lua language.
It's meant to be an improvement over Sublime Text's default autocomplete, which is frequently
cluttered with noise from comments, etc.

Types of autocompletion added:

* Local variables, including function parameters, for loop indices, etc.
* File paths in `require`. This will search along all folders added to the project for Lua files and directories,
and adds them as autocompletion entries when calling the `require` function.

Wishlist:

* Builtins autocompletion.
* Table member completion (really hard!).
