"""
module debian.parse

@author: Ximin Luo <infinity0@gmx.com> 
"""

from code import interact
from collections import namedtuple
from debian.util import Any, dict_append, roundrobin, uninvert_idx


TopLevelParser = Any()
TopLevelParser.keyX = lambda block: (None, [], block)
TopLevelParser.keyU = lambda s, pri, aux: aux


class MKVCParser(namedtuple(
	"MKVCParser", "omaker pselect extraP blockP keyC keyX keyU check_pre check_post")):
	"""Multi-key-value chunk parser.

	block :;
		logical unit of chunks, represented as [chunk]
	primary ::
		primary data of a block, represented as [chunk]
	auxillary ::
		auxillary data of a block (e.g. comments), represented as [chunk]

	@param omaker: primary -> application-level object 
	@param pselect: key -> MKVCParser
	@param extraP: chunk, was_block -> bool
	@param blockP: chunk, was_block -> bool
	@param keyC: keystr -> key
	@param keyX: block -> keystr, [chunk], [chunk]
	@param keyU: keystr, [chunk], [chunk] -> block
	@param check_pre: ( keystr, primary, keyidx, extras -> None )
	@param check_post: ( MKVCState -> None )
	"""

	def use(self, *args, **kwargs):
		return self._replace(*args, **kwargs)

	def add_check_pre(self, check_pre):
		return self._replace(check_pre=self.check_pre + (check_pre,))

	def add_check_post(self, check_post):
		return self._replace(check_post=self.check_post + (check_post,))

	def mkchild(self, parts):
		s, pri, aux = parts
		return self.pselect(self.keyC(s)).parse_parts(s, pri, aux, self)

	def parse(self, block, parent=TopLevelParser):
		s, pri, aux = parent.keyX(block)
		return self.parse_parts(s, pri, aux, parent)

	def parse_parts(self, keystr, primary, auxillary, parent):
		blocks = [[]]  # [block]
		extras = [[]]  # [block]
		was_block = False
		for chunk in auxillary:
			if self.extraP(chunk, was_block):
				if was_block:
					blocks.append([])
					was_block = False
				extras[-1].append(chunk)
			else:
				if not was_block:
					extras.append([])
					was_block = True
				elif self.blockP(chunk, was_block):
					blocks.append([])
				blocks[-1].append(chunk)
		if not blocks[-1]: blocks.pop()

		try:
			allparts = map(self.keyX, blocks)
			keyidx = reduce(
				dict_append,
				((self.keyC(s), i) for i, (s, pri, aux) in enumerate(allparts)),
				{})

			for check_pre in self.check_pre:
				check_pre(keystr, primary, keyidx, extras)
		except Exception, e:
			interact(local=locals())
			raise

		try:
			childs = map(self.mkchild, allparts)
			result = MKVCState(
				self.omaker,
				keystr, primary,
				childs, keyidx, extras,
				parent.keyU)

			for check_post in self.check_post:
				check_post(result)
		except Exception, e:
			interact(local=locals())
			raise

		return result

	def load(self, fn):
		with open(fn) as fp:
			return self.parse(fp)


class MKVCState(namedtuple("MKVCState",
	"omaker keystr primary childs keyidx extras keyU")):
	"""Multi-key-value chunk parser result state.

	@param omaker: primary -> application-level object 
	@param keystr: main key-string for this state
	@param primary: [chunk] main data for this block
	@param childs: [MKVCState]
	@param keyidx: { key: [child_index] }
	@param extras: [[chunk]] extra comments not part of child block
	@param keyU: func: key, [chunk], [chunk] -> [chunk]
	"""

	@property
	def keys(self):
		return uninvert_idx(self.keyidx)

	def model(self):
		return self.omaker(self.primary)

	def get(self, key, d=None):
		idx = self.keyidx.get(key, [])
		return self.childs[idx[-1]] if idx else d

	def getall(self, key):
		return [self.childs[i] for i in self.keyidx.get(key, [])]

	def block(self):
		try:
			return self.keyU(self.keystr, self.primary, self.chunks())
		except Exception, e:
			interact(local=locals)
			raise

	def chunks(self):
		return [
			chunk
			for chunks in roundrobin(
				self.extras,
				(state.block() for state in self.childs))
			for chunk in chunks
			]

	def __str__(self):
		return "".join(self.block())

	def write(self, fp):
		fp.write(self.__str__())

	def inspect(self):
		interact(local=locals())

	def save(self, fn):
		with open(fn, 'w') as fp:
			self.write(fp)

	def pretty(self, idtl=0, idts='\t'):
		return "%r\n%s" % (self.model(), "".join(
		  ("%s%s = %s" % (idts * idtl, k, state.pretty(idtl + 1, idts))
		   for k, state in zip(self.keys, self.childs))
		))


LeafParser = MKVCParser(
	lambda x: x, None,
	lambda chunk, was_block: True, None,
	None,
	None, None,
	(), (),
)
