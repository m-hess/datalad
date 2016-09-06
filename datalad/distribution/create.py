# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""High-level interface for dataset creation

"""

import logging

from os import listdir
from os.path import isdir

from datalad.interface.base import Interface
from datalad.interface.common_opts import git_opts
from datalad.interface.common_opts import annex_opts
from datalad.interface.common_opts import annex_init_opts
from datalad.interface.common_opts import dataset_description
from datalad.interface.common_opts import add_to_superdataset
from datalad.support.constraints import EnsureStr
from datalad.support.constraints import EnsureNone
from datalad.support.constraints import EnsureDType
from datalad.support.param import Parameter
from datalad.support.annexrepo import AnnexRepo
from datalad.support.gitrepo import GitRepo
from datalad.support.gitrepo import to_options
from datalad.utils import getpwd

from .dataset import Dataset
from .dataset import datasetmethod
from .dataset import EnsureDataset


__docformat__ = 'restructuredtext'

lgr = logging.getLogger('datalad.distribution.create')


class Create(Interface):
    """Create a new dataset from scratch.

    This command initializes a new :term:`dataset` at a given location, or the
    current directory. The new dataset can optionally be registered in an
    existing :term:`superdataset` (the new dataset's path needs to be located
    within the superdataset for that, and the superdataset will be detected
    automatically). It is recommended to provide a brief description to label
    the dataset's nature *and* location, e.g. "Michael's music on black
    laptop". This helps humans to identify data locations in distributed
    scenarios.  By default an identifier comprised of user and machine name,
    plus path will be generated.

    Plain Git repositories can be created via the [PY: `no_annex` PY][CMD: --no-annex CMD] flag.
    However, the result will not be a full dataset, and, consequently,
    not all features are supported (e.g. a description).

    || REFLOW >>
    To create a local version of a remote dataset use the
    :func:`~datalad.api.install` command instead.
    << REFLOW ||

    .. note::
      Power-user info: This command uses :command:`git init`, and
      :command:`git annex init` to prepare the new dataset. Registering to a
      superdataset is performed via a :command:`git submodule add` operation
      in the discovered superdataset.
    """

    _params_ = dict(
        path=Parameter(
            args=("path",),
            metavar='PATH',
            doc="""path where the dataset shall be created, directories
            will be created as necessary. If no location is provided, a dataset
            will be created in the current working directory. Either way the
            command will error if the target directory is not empty.
            Use `force` to create a dataset in a non-empty directory.""",
            nargs='?',
            # put dataset 2nd to avoid useless conversion
            constraints=EnsureStr() | EnsureDataset() | EnsureNone()),
        force=Parameter(
            args=("-f", "--force",),
            doc="""enforce creation of a dataset in a non-empty directory""",
            action='store_true'),
        description=dataset_description,
        add_to_super=add_to_superdataset,
        name=Parameter(
            args=("--name",),
            metavar='NAME',
            doc="""name of the dataset within the namespace of it's superdataset.
            By default its path relative to the superdataset is used. Used only
            together with `add_to_super`.""",
            constraints=EnsureStr() | EnsureNone()),
        no_annex=Parameter(
            args=("--no-annex",),
            doc="""if set, a plain Git repository will be created without any
            annex""",
            action='store_true'),
        no_commit=Parameter(
            args=("--no-commit",),
            doc="""if set, do not commit automatically""",
            action='store_true'),
        annex_version=Parameter(
            args=("--annex-version",),
            doc="""select a particular annex repository version. The
            list of supported versions depends on the available git-annex
            version. This should be left untouched, unless you know what
            you are doing""",
            constraints=EnsureDType(int) | EnsureNone()),
        annex_backend=Parameter(
            args=("--annex-backend",),
            constraints=EnsureStr() | EnsureNone(),
            # not listing choices here on purpose to avoid future bugs
            doc="""set default hashing backend used by the new dataset.
            For a list of supported backends see the git-annex
            documentation. The default is optimized for maximum compatibility
            of datasets across platforms (especially those with limited
            path lengths)""",
            nargs=1),
        native_metadata_type=Parameter(
            args=('--native-metadata-type',),
            metavar='LABEL',
            action='append',
            constraints=EnsureStr() | EnsureNone(),
            doc="""Metadata type label. Must match the name of the respective
            parser implementation in Datalad (e.g. "bids").[CMD:  This option
            can be given multiple times CMD]"""),
        git_opts=git_opts,
        annex_opts=annex_opts,
        annex_init_opts=annex_init_opts,
    )

    @staticmethod
    @datasetmethod(name='create', dataset_argname='path')
    def __call__(
            path=None,
            force=False,
            description=None,
            add_to_super=False,
            name=None,
            no_annex=False,
            no_commit=False,
            annex_version=None,
            annex_backend='MD5E',
            native_metadata_type=None,
            git_opts=None,
            annex_opts=None,
            annex_init_opts=None):

        if not isinstance(force, bool):
            raise ValueError("force should be bool, got %r.  Did you mean to provide a 'path'?" % force)
        if path:
            if isinstance(path, Dataset):
                ds = path
            else:
                # this means we are not bound to a Dataset instance.
                # Therefore there is no difference between a relative path and
                # an "explicit" path. Both are based on CWD, since there is no
                # repo or dataset it is passed to. Hence `path` doesn't need to
                # be resolved.
                ds = Dataset(path)
        else:
            ds = Dataset(getpwd())

        # don't create in non-empty directory without `force`:
        if isdir(ds.path) and listdir(ds.path) != [] and not force:
            raise ValueError("Cannot create dataset in directory %s "
                             "(not empty). Use option 'force' in order to "
                             "ignore this and enforce creation." % ds.path)

        if add_to_super:
            sds = ds.get_superdataset()

            if sds is not None:
                return sds.create_subdataset(
                    ds.path,
                    force=force,
                    name=name,
                    description=description,
                    no_annex=no_annex,
                    annex_version=annex_version,
                    annex_backend=annex_backend,
                    git_opts=git_opts,
                    annex_opts=annex_opts,
                    annex_init_opts=annex_init_opts)
            else:
                if isinstance(add_to_super, bool):
                    raise ValueError("No super dataset found for dataset %s" % ds)
                elif add_to_super == 'auto':
                    pass  # we are cool to just make it happen without add_to_super
                else:
                    raise ValueError("Do not know how to handle add_to_super=%s"
                                     % repr(add_to_super))

        if no_annex:
            if description:
                raise ValueError("Incompatible arguments: cannot specify "
                                 "description for annex repo and declaring "
                                 "no annex repo.")
            if annex_opts:
                raise ValueError("Incompatible arguments: cannot specify "
                                 "options for annex and declaring no "
                                 "annex repo.")
            if annex_init_opts:
                raise ValueError("Incompatible arguments: cannot specify "
                                 "options for annex init and declaring no "
                                 "annex repo.")

            lgr.info("Creating a new git repo at %s", ds.path)
            vcs = GitRepo(ds.path, url=None, create=True,
                          git_opts=git_opts)
        else:
            # always come with annex when created from scratch
            lgr.info("Creating a new annex repo at %s", ds.path)
            vcs = AnnexRepo(ds.path, url=None, create=True,
                            backend=annex_backend,
                            version=annex_version,
                            description=description,
                            git_opts=git_opts,
                            annex_opts=annex_opts,
                            annex_init_opts=annex_init_opts)

        if native_metadata_type is not None:
            if not isinstance(native_metadata_type, list):
                native_metadata_type = [native_metadata_type]
            for nt in native_metadata_type:
                ds.config.add('datalad.metadata.nativetype', nt)

        # record the ID of this repo for the afterlife
        # to be able to track siblings and children
        id_var = 'datalad.dataset.id'
        if id_var in ds.config:
            # make sure we reset this variable completely, in case of a re-create
            ds.config.unset(id_var, where='dataset')
        ds.config.add(id_var, ds.id, where='dataset')

        # save everthing
        ds.repo.add('.datalad', git=True)

        if not no_commit:
            vcs.commit(msg="Initial commit",
                       options=to_options(allow_empty=True),
                       _datalad_msg=True)

        return ds

    @staticmethod
    def result_renderer_cmdline(res, args):
        from datalad.ui import ui
        if res is None:
            ui.message("Nothing was created")
        elif isinstance(res, Dataset):
            ui.message("Created dataset at %s." % res.path)
