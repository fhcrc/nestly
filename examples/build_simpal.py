import json, os, glob

homedir = "/cs/researcher/matsen/Overbaugh_J/HIV_Data/"


# general functions
def json_of_file(fname):
  with open(fname, 'r') as ch:
    return(json.load(ch))

def json_to_file(fname, d):
  with open(fname, 'w') as ch:
    ch.write(json.dumps(d, indent=4))

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


# building our dictionaries

control = {
    "ref" : 
    	prep(
	  os.path.join(homedir,"sim/old/clean_fullGenomeLANL/"),
	  ["ag.fasta"]),
    "frag" : 
    	prep(
	  os.path.join(homedir,"sim/beastly/"),
	  ["singly/*/*/*.fasta", "super/*/*/*.fasta"]),
    "beast_template" : 
	prep(
	  os.path.join(homedir,"scripts/beast_corral/"),
	  ["hky.coalescent.xml"]),
    }

order = [
    "ref",
    "beast_template",
    "frag",
    ]

complete = {
    "control": control,
    "order": order,
    }

json_to_file("complete.json", complete)
