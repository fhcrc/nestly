import json, os, glob, copy, re

# general functions
def json_of_file(fname):
    with open(fname, 'r') as ch:
	return(json.load(ch))

def json_to_file(fname, d):
    with open(fname, 'w') as ch:
	ch.write(json.dumps(d, indent=4))

def create_dir(dirname):
    if os.path.isfile(dirname):
	raise IOError("file blocking mkdir")
    if not os.path.isdir(dirname):
	os.mkdir(dirname)

# functions
def path_list_of_pathpair(path, filel):
    return([os.path.join(path, x) for x in filel])

def nonempty_glob(g):
    globbed = glob.glob(g)
    if globbed == []:
	raise IOError("empty glob: "+g)
    else:
	return(globbed)

def nonempty_glob_pathpair(path, globl):
    return(sum([nonempty_glob(g) for g in path_list_of_pathpair(path, globl)], []))

# we choose to strip the extension and then replace all slashes with dashes
def dirname_of_path(path):
    (base,_) = os.path.splitext(path)
    return(re.sub("/","-",base))

def prep(path, globl):
    globbed = nonempty_glob_pathpair(path, globl)
    return([(g, dirname_of_path(re.sub(path, "", g))) for g in globbed])

# the actual recursion
def _aux_build(control, order):
    if not order:
	json_to_file("control.json", control)
	return()
    else:
	json_to_file("precontrol.json", control)
	curr = order[0]
	level_control = copy.copy(control)
	for (fname, dirname) in control[curr]:
	    create_dir(dirname)
	    os.chdir(dirname)
	    level_control[curr] = fname
	    _aux_build(level_control, order[1:])
	    os.chdir("..")

def build(complete):
    _aux_build(complete["control"], complete["order"])
