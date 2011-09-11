"""
module debian.debutil

@author: Ximin Luo <infinity0@gmx.com> 
"""

def cont_test(line):
	return line and line[0].isspace()

def cont_check(line):
	if not line or not line[0].isspace():
		raise SyntaxError("continuation does not start with whitespace: %r" % line)
	return True

def cont_strip(line):
	cont_check(line)
	return "" if line == " ." else line[1:]

def v_single(lines):
	if len(lines) != 1: raise SyntaxError()
	return lines[0].strip()

def v_words(lines):
	return [o.strip() for line in lines for o in line.split()]

def v_list(lines):
	return [line.strip() for line in lines]

def v_text(lines):
	return [cont_strip(line) for line in lines]

def v_text_synop(lines):
	lines = iter(lines)
	return (next(lines).strip(), v_text(lines))
