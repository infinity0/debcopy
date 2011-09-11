"""
module debian.util

@author: Ximin Luo <infinity0@gmx.com> 
"""

from itertools import cycle, islice


class Any(object): pass


def roundrobin(*iterables):
	"roundrobin('ABC', 'D', 'EF') --> A D E B F C"
	# Recipe credited to George Sakkis
	pending = len(iterables)
	nexts = cycle(iter(it).next for it in iterables)
	while pending:
		try:
			for next in nexts:
					yield next()
		except StopIteration:
			pending -= 1
			nexts = cycle(islice(nexts, pending))

def dict_append(d, p):
	k, v = p
	d.setdefault(k, []).append(v)
	return d

def freq(items):
	d = {}
	for it in items:
		d[it] = d.get(it, 0) + 1
	return d

def uninvert_idx(keyidx):
	kk = []
	for k, ii in keyidx.iteritems():
		for i in ii:
			li = len(kk) - 1
			if i > li:
				kk.extend([None]*(i - li))
			kk[i] = k
	return kk

def itercut(pred, it):
	it = iter(it)
	a, b = [], []
	for i in it:
		if pred(i):
			a.append(i)
		else:
			b.append(i)
			break
	b.extend(it)
	return a, b
