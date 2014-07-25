
import sublime, sublime_plugin
from LuaAutocomplete.locals import LocalsFinder

class ExampleCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, "Hello, World!")

class LuaAutocomplete(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		if view.settings().get("syntax") != "Packages/Lua/Lua.tmLanguage":
			# Not Lua, don't do anything.
			return
		
		location = locations[0] # TODO: Better multiselect behavior?
		src = view.substr(sublime.Region(0, view.size()))
		
		localsfinder = LocalsFinder(src)
		varz = localsfinder.run(location)
		
		return [(name+"\t"+data.vartype,name) for name, data in varz.items()], sublime.INHIBIT_WORD_COMPLETIONS
