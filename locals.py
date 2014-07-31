
from collections import OrderedDict, namedtuple
from copy import copy
import logging
import re

logger = logging.getLogger("LuaAutocomplete.locals")

localvar_re = re.compile(r"(?:[a-zA-Z_][a-zA-Z0-9_]*|\.\.\.)")

class StopParsing(Exception):
	pass

# Holds info about a variable.
# vartype: Semantic info about the origins of a variable, ex. if it's a local var, a for loop index, an upvalue, ...
VarInfo = namedtuple("VarInfo", ["vartype"])

class LocalsFinder:
	"""
	Parses a Lua file, looking for local variables that are in a certain scope.
	"""
	
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
		"""
		Creates a new parser.
		"""
		self.code = code
	
	def run(self, cursor):
		"""
		Runs the parser. cursor is the location of the scope.
		"""
		self.matches = OrderedDict()
		self.scope_stack = [{}]
		
		self.setup_initial_matches()
		
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
		
		curscope = self.scope_stack[-1]
		del self.matches
		del self.scope_stack
		return curscope
	
	def setup_initial_matches(self):
		for name, regex in self.patterns.items():
			self.matches[name] = regex.search(self.code)
	
	def rematch(self, pos):
		best_name, best_match = None, None
		
		for name, regex in self.patterns.items():
			match = self.matches[name]
			
			if not match:
				# Previous try didn't find anything. Trying now won't find anything either.
				continue
			
			# If the new position is less than the first match, the regex doesn't need to be re-ran.
			if pos > match.start():
				match = regex.search(self.code, pos)
				self.matches[name] = match
			
			# Find first match
			if match and (not best_match or match.start() < best_match.start()):
				best_name = name
				best_match = match
		return best_name, best_match
	
	def dispatch(self, name, match):
		logger.debug("Matched %s at char %s", name, match.start())
		return getattr(self, "handle_"+name)(match)
	
	def push_scope(self, is_function=False):
		if not is_function:
			self.scope_stack.append(self.scope_stack[-1].copy())
		else:
			newscope = {}
			for k, v in self.scope_stack[-1].items():
				v2 = VarInfo(vartype="upvalue")
				newscope[k] = v2
			self.scope_stack.append(newscope)
	
	def pop_scope(self):
		if len(self.scope_stack) == 1:
			logging.debug("Scope stack underflow; probably an excess `end`")
			# TODO: Can we handle excessive ends better?
		else:
			self.scope_stack.pop()
	
	def add_var(self, name, **kwargs):
		self.scope_stack[-1][name] = VarInfo(**kwargs)
	
	def add_vars(self, vars, **kwargs):
		info = VarInfo(**kwargs)
		for name in vars:
			self.scope_stack[-1][name] = info
	
	#########################################################################
	
	def handle_for_incremental(self, match):
		self.push_scope()
		
		self.add_var(match.group(1), vartype="for index")
		return match.end()
	
	def handle_for_iterator(self, match):
		self.push_scope()
		
		the_locals = localvar_re.findall(match.group(1))
		self.add_vars(the_locals, vartype="for index")
		return match.end()
	
	def handle_local_function(self, match):
		self.add_var(match.group(1), vartype="local")
		
		self.push_scope(is_function=True)
		arguments = localvar_re.findall(match.group(2))
		self.add_vars(arguments, vartype="parameter")
		return match.end()
	
	def handle_function(self, match):
		self.push_scope(is_function=True)
		arguments = localvar_re.findall(match.group(1))
		self.add_vars(arguments, vartype="parameter")
		return match.end()
	
	def handle_method(self, match):
		self.push_scope(is_function=True)
		arguments = localvar_re.findall(match.group(1))
		self.add_var("self", vartype="self")
		self.add_vars(arguments, vartype="parameter")
		return match.end()
	
	def handle_block_start(self, match):
		self.push_scope()
		return match.end()
	
	def handle_block_end(self, match):
		self.pop_scope()
		return match.end()
	
	def handle_locals(self, match):
		the_locals = localvar_re.findall(match.group(1))
		self.add_vars(the_locals, vartype="local")
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
	import sys
	logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
	
	fname = sys.argv[1]
	loc = int(sys.argv[2])
	
	with open(fname, "r") as f:
		contents = f.read()
	
	finder = LocalsFinder(contents)
	for i in range(1):
		scope = finder.run(loc)
		if i == 0:
			print(scope)
