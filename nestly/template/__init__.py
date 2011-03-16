import importlib

BACKENDS = {
   'stringtemplate': 'stringtemplate',
   'stringformat': 'stringformat',
}

def get_template_engine(name):
    name = 'nestly.template.backend.%s' % BACKENDS[name]
    module = importlib.import_module(name)
    return getattr(module, 'render')
