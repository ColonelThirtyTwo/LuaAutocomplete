
LuaAutocomplete
===============

This is a very basic auto-completion plugin for Sublime Text 3 and the Lua language.
It's meant to be an improvement over Sublime Text's default autocomplete, which is frequently
cluttered with noise from comments, etc.

Only local variables are autocompleted at the moment. This includes function parameters and for
loop indices, but not globals or table contents (as those are hard to detect for dynamically-typed
languages).
