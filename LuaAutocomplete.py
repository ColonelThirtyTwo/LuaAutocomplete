
import sublime, sublime_plugin
import re, os, itertools
from LuaAutocomplete.locals import LocalsFinder

class LocalsAutocomplete(sublime_plugin.EventListener):
	@staticmethod
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
	
	def on_query_completions(self, view, prefix, locations):
		if view.settings().get("syntax") != "Packages/Lua/Lua.tmLanguage":
			# Not Lua, don't do anything.
			return
		
		location = locations[0] # TODO: Better multiselect behavior?
		
		if not LocalsAutocomplete.can_local_autocomplete(view, location):
			return
		
		src = view.substr(sublime.Region(0, view.size()))
		
		localsfinder = LocalsFinder(src)
		varz = localsfinder.run(location)
		
		return [(name+"\t"+data.vartype,name) for name, data in varz.items()], sublime.INHIBIT_WORD_COMPLETIONS

class RequireAutocomplete(sublime_plugin.EventListener):
	
	@staticmethod
	def filter_lua_files(filenames):
		for f in filenames:
			fname, ext = os.path.splitext(f)
			if ext == ".lua" or ext == ".luac":
				yield fname
	
	def on_query_completions(self, view, prefix, locations):
		if view.settings().get("syntax") != "Packages/Lua/Lua.tmLanguage":
			# Not Lua, don't do anything.
			return
		
		proj_file = view.window().project_file_name()
		if not proj_file:
			# No project
			return
		
		location = locations[0]
		src = view.substr(sublime.Region(0, location))
		
		match = re.search(r"""require\s*\(?\s*["']([^"]*)$""", src)
		if not match:
			return
		
		module_path = match.group(1).split(".")
		
		results = []
		proj_dir = os.path.dirname(proj_file)
		
		for proj_subdir in view.window().project_data()["folders"]:
			proj_subdir = proj_subdir["path"]
			cur_path = os.path.join(proj_dir, proj_subdir, *(module_path[:-1]))
			print("curpath:", cur_path)
			if not os.path.exists(cur_path) or not os.path.isdir(cur_path):
				continue
			
			_, dirs, files = next(os.walk(cur_path)) # walk splits directories and regular files for us
			
			results.extend(map(lambda x: (x+"\tsubdirectory", x+"."), dirs))
			results.extend(map(lambda x: (x+"\tmodule", x), RequireAutocomplete.filter_lua_files(files)))
		
		return results, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
