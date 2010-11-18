import json, os, glob, copy, re, collections

# NamedVal
NV = collections.namedtuple('NamedValue', 'name val')

def file_nv(path):
    (base,_) = os.path.splitext(path)
    return(NV(name = os.path.basename(base), val = path))

def dir_nv(path):
    return(NV(name = os.path.basename(path), val = path))

def base_nv(val):
    base = os.path.basename(path)
    return(NV(name = base, val = base))

# general functions
def json_of_file(fname):
    with open(fname, 'r') as ch:
	return(json.load(ch))

def json_to_file(fname, d):
    with open(fname, 'w') as ch:
	ch.write(json.dumps(d, indent=4))

def create_dir(dirname):
    if os.path.isfile(dirname):
	raise IOError("file blocking mkdir: "+dirname)
    if not os.path.isdir(dirname):
	os.mkdir(dirname)

def assert_extant(fname):
    if not(os.path.isfile(fname)):
	raise IOError("file does not exist: "+fname)

# functions
def path_list_of_pathpair(path, filel):
    return([os.path.join(path, x) for x in filel])

def nonempty_glob(g):
    globbed = glob.glob(g)
    if globbed == []:
	raise IOError("empty glob: "+g)
    else:
	return(globbed)

def collect_globs(path, globl):
    return(sum([nonempty_glob(g) for g in path_list_of_pathpair(path, globl)], []))

def all_choices(how, path, filel):
    return(lambda(_): map(how, path_list_of_pathpair(path, filel)))

def all_globs(how, path, globl):
    return(lambda(_): map(how, collect_globs(path, globl)))

# we choose to strip the extension and then replace all slashes with dashes
def dirname_of_path(path):
    (base,_) = os.path.splitext(path)
    return(re.sub("/","-",base))

# the actual recursion
def _aux_build(control, order):
    if not order:
	json_to_file("control.json", control)
	return()
    else:
	# json_to_file("precontrol.json", control)
	curr = order[0]
	level_control = copy.copy(control)
	for nv in control[curr](control):
	    # we only want to make one directory level at a time:
	    assert(not (re.search("/", nv.name)))
	    create_dir(nv.name)
	    os.chdir(nv.name)
	    level_control[curr] = nv.value
	    _aux_build(level_control, order[1:])
	    os.chdir("..")

def build(complete):
    _aux_build(complete["control"], complete["order"])
