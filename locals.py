
import re
from collections import OrderedDict
import logging

logger = logging.getLogger("LuaAutocomplete.locals")

localvar_re = re.compile(r"(?:[a-zA-Z_][a-zA-Z0-9_]*|\.\.\.)")

class StopParsing(Exception):
	pass

class LocalsFinder:
	# Both patterns and matches need to be ordered, so that `longcomment` is tried first before `comment`
	patterns = OrderedDict([
		("for_incremental", re.compile(r"\bfor\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=.*?\bdo\b", re.S)),
		("for_iterator",    re.compile(r"\bfor\s*((?:[a-zA-Z_][a-zA-Z0-9_]*|,\s*)+)\s*in\b.*?\bdo\b", re.S)),
		("local_function",  re.compile(r"\blocal\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(((?:[a-zA-Z_][a-zA-Z0-9_]*|\.\.\.|,\s*)*)\)")),
		("function",        re.compile(r"\bfunction(?:\s+[a-zA-Z0-9._]*)?\(((?:[a-zA-Z_][a-zA-Z0-9_]*|\.\.\.|,\s*)*)\)")),
		("method",          re.compile(r"\bfunction\s+[a-zA-Z0-9._]+:[a-zA-Z0-9_]+\(((?:[a-zA-Z_][a-zA-Z0-9_]*|\.\.\.|,\s*)*)\)")),
		("block_start",     re.compile(r"\b(?:do|then|repeat)\b")), # Matches while loops, incomplete for loops, and `do ... end` blocks
		("block_end",       re.compile(r"\b(?:end|until)\b")),
		("locals",          re.compile(r"\blocal\s+((?:[a-zA-Z_][a-zA-Z0-9_]*|,\s*)+)\b")),
		("longcomment",     re.compile(r"\-\-\[(=*)\[")),
		("comment",         re.compile(r"\-\-")),
		("string",          re.compile(r"""(?:"|')""")),
		("longstring",      re.compile(r"\[(=*)\[")),
	])
	
	def __init__(self, code):
		self.code = code
		self.matches = OrderedDict()
		self.scope_stack = [set()]
	
	def run(self, cursor):
		try:
			current_pos = 0
			while True:
				name, match = self.rematch(current_pos)
				if not match:
					break
				
				if match.start() >= cursor:
					break
				
				current_pos = self.dispatch(name, match)
		except StopParsing:
			pass
		
		return self.scope_stack[-1]
	
	def rematch(self, pos):
		for name, regex in self.patterns.items():
			self.matches[name] = regex.search(self.code, pos)
		return min(self.matches.items(), key=lambda x: float("inf") if not x[1] else x[1].start())
	
	def dispatch(self, name, match):
		logger.debug("Matched %s at char %s", name, match.start())
		return getattr(self, "handle_"+name)(match)
	
	def push_scope(self):
		self.scope_stack.append(self.scope_stack[-1].copy())
	
	def pop_scope(self):
		if len(self.scope_stack) == 1:
			logging.debug("Scope stack underflow; probably an excess `end`")
			# TODO: Can we handle excessive ends better?
		else:
			self.scope_stack.pop()
	
	def add_vars(self, *args):
		self.scope_stack[-1].update(args)
	
	
	def handle_for_incremental(self, match):
		self.push_scope()
		
		self.add_vars(match.group(1))
		return match.end()
	
	def handle_for_iterator(self, match):
		self.push_scope()
		
		the_locals = localvar_re.findall(match.group(1))
		self.add_vars(*the_locals)
		return match.end()
	
	def handle_local_function(self, match):
		self.add_vars(match.group(1))
		
		self.push_scope()
		arguments = localvar_re.findall(match.group(2))
		self.add_vars(*arguments)
		return match.end()
	
	def handle_function(self, match):
		self.push_scope()
		arguments = localvar_re.findall(match.group(1))
		self.add_vars(*arguments)
		return match.end()
	
	def handle_method(self, match):
		self.push_scope()
		arguments = localvar_re.findall(match.group(1))
		self.add_vars("self", *arguments)
		return match.end()
	
	def handle_block_start(self, match):
		self.push_scope()
		return match.end()
	
	def handle_block_end(self, match):
		self.pop_scope()
		return match.end()
	
	def handle_locals(self, match):
		the_locals = localvar_re.findall(match.group(1))
		self.add_vars(*the_locals)
		return match.end()
	
	def handle_comment(self, match):
		line_end = self.code.find("\n", match.end())
		if line_end == -1:
			raise StopParsing() # EOF
		return line_end+1
	
	def handle_longcomment(self, match):
		end_str = "]" + match.group(1) + "]" # Match number of equals signs
		comment_end = self.code.find(end_str, match.end())
		if comment_end == -1:
			raise StopParsing() # EOF
		return comment_end+len(end_str)
	
	def handle_string(self, match):
		str_char = match.group(0) # single or double quotes?
		str_end = match.end()
		
		while self.code[str_end] != str_char or self.code[str_end-1] == "\\": # Keep looking for unescaped terminator
			str_end = self.code.find(str_char, str_end+1)
			if str_end == -1:
				raise StopParsing() # EOF
		
		return str_end+1
	
	def handle_longstring(self, match):
		end_str = "]" + match.group(1) + "]" # Match number of equals signs
		str_end = self.code.find(end_str, match.end())
		if str_end == -1:
			raise StopParsing() # EOF
		return str_end+len(end_str)

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
	
	finder = LocalsFinder(r"""
		
local oop = require "oop"

local Component, super = oop.Class(...)

Component.DEFAULTNAME = "I am \" nn \x4fa0"

number = 444

local a, b, c = 1, 2, 3

foooooooo = 123

local n = bork()["foo"]()

bork()

function Component.__init(class)
	return super.__init(class)
end

function Component:init(obj, name)
	self.obj = obj
	self.name = name
	
end

function Component:destroy()
	self.obj = nil
	self.name = nil
end

function Component:serialize()
	return {
		_name = self.name,
	}
end

return Component

	""")
	print(finder.run(344))
