# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""

"""

__docformat__ = 'restructuredtext'

import logging
from glob import glob
from os.path import join as opj, basename, dirname
from importlib import import_module

from datalad.support.param import Parameter
from datalad.support.constraints import EnsureNone
from datalad.distribution.dataset import EnsureDataset
from datalad.distribution.dataset import datasetmethod
from datalad.distribution.dataset import require_dataset
from datalad.dochelpers import exc_str

from datalad.interface.base import Interface
from datalad.interface.utils import build_doc

lgr = logging.getLogger('datalad.plugin')


def _get_plugin_names():
    basepath = dirname(__file__)
    return [basename(e)[:-3]
            for e in glob(opj(basepath, '*.py'))
            if not e.endswith('__init__.py')]


@build_doc
class Plugin(Interface):
    """Export a dataset to another representation
    """
    # XXX prevent common args from being added to the docstring
    _no_eval_results = True

    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the dataset to export. If
            no dataset is given, an attempt is made to identify the dataset
            based on the current working directory.""",
            constraints=EnsureDataset() | EnsureNone()),
        plugin=Parameter(
            args=("plugin",),
            choices=_get_plugin_names(),
            doc="""label of the type or format the dataset shall be exported
            to."""),
        output=Parameter(
            args=('-o', '--output'),
            doc="""output destination specification to be passes to the exporter.
            The particular semantics of the option value depend on the actual
            exporter. Typically, this will be a file name or a path to a
            directory."""),
        showpluginhelp=Parameter(
            args=('-H', '--show-plugin-help',),
            dest='showpluginhelp',
            action='store_true',
            doc="""show help for a specific plugin"""),
    )

    @staticmethod
    @datasetmethod(name='plugin')
    def __call__(plugin, dataset=None, showpluginhelp=False, output=None, **kwargs):
        # get a handle on the relevant plugin module
        import datalad.plugin as plugin_mod
        try:
            pluginmod = import_module('.%s' % (plugin,), package=plugin_mod.__package__)
        except ImportError as e:
            raise ValueError("cannot load plugin '{}': {}".format(
                plugin, exc_str(e)))
        if showpluginhelp:
            # no result, but return the module to make the renderer do the rest
            return (pluginmod, None)

        ds = require_dataset(dataset, check_installed=True, purpose='plugin')
        # call the plugin, either with the argv array from the cmdline call
        # or directly with the kwargs
        if 'datalad_unparsed_args' in kwargs:
            result = pluginmod._datalad_plugin_call(
                ds, argv=kwargs['datalad_unparsed_args'], output=output)
        else:
            result = pluginmod._datalad_plugin_call(
                ds, output=output, **kwargs)
        return (pluginmod, result)

    @staticmethod
    def result_renderer_cmdline(res, args):
        pluginmod, result = res
        if args.showpluginhelp:
            # the function that prints the help was returned as result
            if not hasattr(pluginmod, '_datalad_get_plugin_help'):
                lgr.error("plugin '{}' does not provide help".format(pluginmod))
                return
            replacement = []
            help = pluginmod._datalad_get_plugin_help()
            if isinstance(help, tuple):
                help, replacement = help
            if replacement:
                for in_s, out_s in replacement:
                    help = help.replace(in_s, out_s + ' ' * max(0, len(in_s) - len(out_s)))
            print(help)
            return
        # TODO call exporter function (if any)
