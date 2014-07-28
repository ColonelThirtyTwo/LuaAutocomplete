
import sublime, sublime_plugin
from LuaAutocomplete.locals import LocalsFinder

def can_local_autocomplete(view, location):
	"""
	Returns true if locals autocompetion makes sense in the specified location (ex. its not indexing a variable, in a string, ...)
	"""
	pos = view.find_by_class(location, False, sublime.CLASS_WORD_START)
	if pos == 0:
		return True
	
	scope_name = view.scope_name(location)
	if "string." in scope_name or "comment." in scope_name:
		# In a string or comment
		return False
	
	if "parameter" in scope_name:
		# Specifying parameters
		return False
	
	char = view.substr(pos-1)
	if char == "." or char == ":":
		# Indexing a value
		return False
	
	return True

class LuaAutocomplete(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		if view.settings().get("syntax") != "Packages/Lua/Lua.tmLanguage":
			# Not Lua, don't do anything.
			return
		
		location = locations[0] # TODO: Better multiselect behavior?
		
		if not can_local_autocomplete(view, location):
			return
		
		src = view.substr(sublime.Region(0, view.size()))
		
		localsfinder = LocalsFinder(src)
		varz = localsfinder.run(location)
		
		return [(name+"\t"+data.vartype,name) for name, data in varz.items()], sublime.INHIBIT_WORD_COMPLETIONS
