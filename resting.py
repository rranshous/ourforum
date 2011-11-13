from flask import Flask
from restful.api import api, setup as setup_restful
import models.restful_models
import validators.restful_validators

def get_models_dict():
    Entity = models.restful_models.Entity
    f = {}
    for attr in dir(models.restful_models):
        o = getattr(models.restful_models,attr)
        try:
            if issubclass(o,Entity):
                f[attr] = o
        except TypeError:
            # not a class, woops,
            pass
    print 'f: %s' % f
    return f


# setup the models
models.restful_models.setup()

# setup the restful lib
setup_restful(models.restful_models,
              validators.restful_validators)

app = Flask(__name__)
app.register_module(api, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True)
