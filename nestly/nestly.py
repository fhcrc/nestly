import json, os, glob, copy, re, collections

## internals
def d_of_jsonfile(fname):
    with open(fname, 'r') as ch:
	return(json.load(ch))

def d_to_jsonfile(fname, d):
    with open(fname, 'w') as ch:
	ch.write(json.dumps(d, indent=4)+"\n")

def nvd_to_jsonfile(fname, d):
    d_to_jsonfile(fname, 
	    collections.OrderedDict([(k, v.val) for (k, v) in d.items()]))

def create_dir(dirname):
    """only makes a directory if needed, and complains if it's blocked by a file"""
    if os.path.isfile(dirname):
	raise IOError("file blocking mkdir: "+dirname)
    if not os.path.isdir(dirname):
	os.mkdir(dirname)

def assert_extant(fname):
    if not(os.path.isfile(fname) or os.path.isdir(fname)):
	raise IOError("path does not exist: "+fname)

def filter_dir(pathl):
    [path for path in pathl if os.path.isdir(path)]


## public

NV = collections.namedtuple('NamedValue', 'name val')

## nv makers: these are various ways of making nv's out of path names
def file_nv(path):
    """make an nv which takes its name from the basename of the path with the suffix taken off"""
    (base,_) = os.path.splitext(path)
    return(NV(name = os.path.basename(base), val = path))

def dir_nv(path):
    """make an nv which takes its name from the basename"""
    return(NV(name = os.path.basename(path), val = path))

def none_nv(path):
    """make a noname nv, which then will not make a directory"""
    return(NV(name = None, val = path))


## functions

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

def filter_dir(pathl):
    return([path for path in pathl if os.path.isdir(path)])

# the all_* functions make lambdas that don't do anything interesting with their argument
def all_choices(how, path, filel):
    """used when we can list all of the files of interest"""
    return(lambda(_): map(how, path_list_of_pathpair(path, filel)))

def all_globs(how, path, globl):
    """used when we want all of a certain list of globs"""
    return(lambda(_): map(how, collect_globs(path, globl)))

def all_dir_globs(how, path, globl):
    """just take the directories out of the globs"""
    return(lambda(_): map(how, filter_dir(collect_globs(path, globl))))

def mirror_dir(start_path, start_paraml, control):
    """mirror a directory tree"""
    # recur by taking all globs from previous dir
    def aux(paraml):
	if 1 < len(paraml):
	    control[paraml[1]] = (
		lambda(c): map(dir_nv, filter_dir(collect_globs(c[paraml[0]].val, "*"))))
	    aux(paraml[1:])
    # start recursion by doing all directories
    if start_paraml:
	control[start_paraml[0]] = all_dir_globs(dir_nv, start_path, ["*"])
        aux(start_paraml)

# we choose to strip the extension and then replace all slashes with dashes
def dirname_of_path(path):
    (base,_) = os.path.splitext(path)
    return(re.sub("/","-",base))

# the actual recursion
def _aux_build(control, paraml):
    if not paraml:
	nvd_to_jsonfile("control.json", control)
	return()
    else:
	# json_to_file("precontrol.json", control)
	curr = paraml[0]
	level_control = copy.copy(control)
	for nv in control[curr](control):
	    level_control[curr] = nv
	    if nv.name:
		# if there is a name then we make a directory
		# below: we only want to make one directory level at a time
    	        assert(not (re.search("/", nv.name)))
    	        create_dir(nv.name)
    	        os.chdir(nv.name)
    	        _aux_build(level_control, paraml[1:])
    	        os.chdir("..")
	    else:
		# no name-- just recur through
		_aux_build(level_control, paraml[1:])

def build(complete):
    destdir = complete["destdir"]
    create_dir(destdir)
    os.chdir(destdir)
    control = complete["control"]
    _aux_build(control, control.keys())
