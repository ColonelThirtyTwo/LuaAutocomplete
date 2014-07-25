
import sublime, sublime_plugin
from LuaAutocomplete.locals import LocalsFinder

def is_indexing(view, location):
	"""
	Returns true if indexing a value; that is, there is a period or colon to the left of the autocompleting word
	"""
	pos = view.find_by_class(location, False, sublime.CLASS_WORD_START)
	if pos == 0:
		return False
	char = view.substr(pos-1)
	return char == "." or char == ":"

class LuaAutocomplete(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		if view.settings().get("syntax") != "Packages/Lua/Lua.tmLanguage":
			# Not Lua, don't do anything.
			return
		
		location = locations[0] # TODO: Better multiselect behavior?
		
		if is_indexing(view, location):
			# Don't bother trying to autocomplete value indexing.
			return
		
		src = view.substr(sublime.Region(0, view.size()))
		
		localsfinder = LocalsFinder(src)
		varz = localsfinder.run(location)
		
		return [(name+"\t"+data.vartype,name) for name, data in varz.items()], sublime.INHIBIT_WORD_COMPLETIONS
