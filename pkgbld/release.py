"""
Policy Simulaton Library (PSL) model Anaconda-Cloud package release logic.
"""
# CODING-STYLE CHECKS:
# pycodestyle release.py
# pylint --disable=locally-disabled release.py

import os
import re
import sys
import time
import shutil
import pkgbld.utils as u


GITHUB_URL = 'https://github.com/PSLmodels'
ANACONDA_USER = 'pslmodels'
ANACONDA_CHANNEL = ANACONDA_USER
HOME_DIR = os.path.expanduser('~')
ANACONDA_TOKEN_FILE = os.path.join(
    HOME_DIR,
    '.{}_anaconda_token'.format(ANACONDA_USER)
)
ANACONDA_TOKEN = os.environ.get("CONDA_TOKEN", None)
WORKING_DIR = os.path.join(
    HOME_DIR,
    'temporary_pkgbld_working_dir'
)
BUILDS_DIR = 'pkgbld_output'


def release(repo_name, pkg_name, version, local=False, dryrun=False,
            channels=None):
    """
    If local==False, conduct build using cloned source code and
    upload to Anaconda Cloud conda packages for each operating-system
    platform and Python version for the specified Policy Simulation Library
    (PSL) model and GitHub release version.

    If local==True, build from source code in current working directory and
    skip the convert and upload steps instead installing the built package on
    the local computer.

    Parameters
    ----------
    repo_name: string
        model repository name appended to GITHUB_URL

    pkg_name: string
        model package name for repository specified by repo_name

    version: string
        model version string having X.Y.Z semantic-versioning pattern;
        must be a release tag in the model repository

    local: boolean
        whether or not to build/install local package

    dryrun: boolean
        whether or not just the package build/upload plan is shown

    channels: list
        list of packages to include in addition to pslmodels and defaults.

    Raises
    ------
    ValueError:
        if parameters are not valid
        if ANACONDA_TOKEN_FILE does not exist

    Returns
    -------
    Nothing

    Notes
    -----
    Example usage: release('Tax-Calculator', 'taxcalc', '1.0.1')
    """
    # pylint: disable=too-many-statements,too-many-locals,too-many-branches

    # check parameters
    if not isinstance(repo_name, str):
        raise ValueError('repo_name is not a string object')
    if not isinstance(pkg_name, str):
        raise ValueError('pkg_name is not a string object')
    if not isinstance(version, str):
        raise ValueError('version is not a string object')
    if not isinstance(local, bool):
        raise ValueError('local is not a boolean object')
    if local:
        cwd = os.getcwd()
        if not cwd.endswith(repo_name):
            msg = ('ERROR: cwd={} does not correspond to '
                   'REPOSITORY_NAME={}\n'.format(cwd, repo_name))
            raise ValueError(msg)
        local_pkgname = os.path.join('.', pkg_name)
        if not os.path.isdir(local_pkgname):
            msg = ('ERROR: cwd={} does not contain '
                   'subdirectory {} '.format(cwd, pkg_name))
            raise ValueError(msg)
    if not isinstance(dryrun, bool):
        raise ValueError('dryrun is not a boolean object')
    pattern = r'^[0-9]+\.[0-9]+\.[0-9]+$'
    if re.match(pattern, version) is None:
        msg = 'version={} does not have X.Y.Z semantic-versioning pattern'
        raise ValueError(msg.format(version))

    # show execution plan
    print(': Package-Builder will build model packages for:')
    print(':   repository_name = {}'.format(repo_name))
    print(':   package_name = {}'.format(pkg_name))
    print(':   model_version = {}'.format(version))
    print(':   additional channels= {}'.format(channels))
    if local:
        print(': Package-Builder will install package on local computer')
    else:
        print(': Package-Builder will upload model packages to:')
        print(':   Anaconda channel = {}'.format(ANACONDA_CHANNEL))
        print(':   using token in file = {}'.format(ANACONDA_TOKEN_FILE))
    if dryrun:
        print(': Package-Builder is quitting')
        return

    # show date and time
    print((': Package-Builder is starting at {}'.format(time.asctime())))

    # remove any old working directory
    if os.path.isdir(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)

    # copy model source code to working directory
    if local:
        # copy source tree on local computer
        print(': Package-Builder is copying local source code')
        destination = os.path.join(WORKING_DIR, repo_name)
        ignorepattern = shutil.ignore_patterns('*.pyc', '*.html', 'test_*')
        shutil.copytree(cwd, destination, ignore=ignorepattern)
        os.chdir(WORKING_DIR)
    else:
        # clone code for model_version from model repository
        print((': Package-Builder is cloning repository code '
               'for {}'.format(version)))
        os.mkdir(WORKING_DIR)
        os.chdir(WORKING_DIR)
        cmd = 'git clone --branch {} --depth 1 {}/{}/'.format(
            version, GITHUB_URL, repo_name
        )
        u.os_call(cmd)
    os.chdir(repo_name)

    # specify version in several repository files
    print(': Package-Builder is setting version')
    # ... specify version in meta.yaml file
    u.file_revision(
        filename=os.path.join('conda.recipe', 'meta.yaml'),
        pattern=r'version: .*',
        replacement='version: {}'.format(version)
    )
    # ... specify version in setup.py file
    u.file_revision(
        filename='setup.py',
        pattern=r'version = .*',
        replacement='version = "{}"'.format(version)
    )
    # ... specify version in package_name/__init__.py file
    u.file_revision(
        filename=os.path.join(pkg_name, '__init__.py'),
        pattern=r'__version__ = .*',
        replacement='__version__ = "{}"'.format(version)
    )

    channel_str = ""
    for channel in channels or []:
        channel_str += f" --channel {channel}"
    channel_str += f" --channel defaults --channel {ANACONDA_CHANNEL}"

    if local:
        u.os_call("conda config --set anaconda_upload no")
    else:
        u.os_call("conda config --set anaconda_upload yes")

    # build and upload model package for each Python version and OS platform
    print(': Package-Builder is building package')
    # Check environment before file.
    TOKEN = ANACONDA_TOKEN or ANACONDA_TOKEN_FILE
    cmd = (
        f"conda build conda.recipe/ --token {TOKEN} --user {ANACONDA_USER} "
        f"--output-folder {BUILDS_DIR} --override-channels {channel_str}"
    )
    u.os_call(cmd)

    if local:
        # do uninstall and install on local computer
        print(': Package-Builder is uninstalling any existing package')
        cmd = 'conda uninstall {} --yes'.format(pkg_name)
        u.os_call(cmd, ignore_error=True)
        print(': Package-Builder is installing package on local computer')
        pkg_dir = os.path.join('file://', WORKING_DIR,
                               repo_name, 'pkgbld_output')
        cmd = 'conda install --channel {} {}={} --yes'
        u.os_call(cmd.format(pkg_dir, pkg_name, version))

    print(': Package-Builder is cleaning-up')

    # remove local packages made during this process
    cmd = 'conda build purge'
    u.os_call(cmd)

    # remove working directory and its contents
    os.chdir(HOME_DIR)
    shutil.rmtree(WORKING_DIR)

    print(': Package-Builder is finishing at {}'.format(time.asctime()))
