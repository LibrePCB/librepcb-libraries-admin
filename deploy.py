#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Administrate LibrePCB Libraries

Usage:
  deploy.py [--token=<token>] [--upgrade=<version>] [--apply] [<library>...]
  deploy.py (-h | --help)

Options:
  -h --help             Show this screen.
  --token=<token>       GitHub API token.
  --upgrade=<version>   Upgrade the libraries to a new file format using the
                        given tag for the librepcb/librepcb-cli Docker image.
  --apply               Apply the required changes.
  <library>             Name of the library repositories to deploy (e.g.
                        "LibrePCB_Base.lplib"). If none is passed, all
                        libraries are deployed.

"""
import os
import json
from distutils.dir_util import copy_tree
from subprocess import check_call, check_output
from docopt import docopt
from github import Github, Label


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
FILES_DIR = os.path.join(ROOT_DIR, 'files')
CACHE_DIR = os.path.join(ROOT_DIR, 'cache')

LABELS = {
    'addition': {
        'description': 'New library element.',
        'color': 'eae435',
    },
    'enhancement': {
        'description': 'Improving an existing library element.',
        'color': 'a2eeef',
    },
    'bug': {
        'description': 'An existing library element contains issues.',
        'color': 'd73a4a',
    },
    'fix': {
        'description': 'Fix an error in an existing library element.',
        'color': 'e99695',
    },
    'ready for review': {
        'description': 'Waiting for review by maintainers.',
        'color': '2164e0',
    },
    'needs corrections': {
        'description': 'Pull request needs corrections before next review.',
        'color': 'c9adff',
    },
    'blocked': {
        'description': 'Blocked by other, dependent pull requests or issues.',
        'color': '353535',
    },
}


def deploy_labels(repo, apply):
    existing_labels = []
    for label in repo.get_labels():
        existing_labels.append(label.name)
        if label.name in LABELS:
            update = False

            # description
            new_description = LABELS[label.name]['description']
            if label.description != new_description:
                print('  - CHANGE label description "{}": "{}" -> "{}"'.format(
                    label.name, label.description, new_description))
                update = True

            # color
            new_color = LABELS[label.name]['color']
            if label.color != new_color:
                print('  - CHANGE label color "{}": "{}" -> "{}"'.format(
                    label.name, label.color, new_color))
                update = True

            if update and apply:
                label.edit(name=label.name, color=new_color,
                           description=new_description)
        else:
            # remove
            print('  - REMOVE label "{}"'.format(label.name))
            if apply:
                label.delete()
    for name, properties in LABELS.items():
        if name not in existing_labels:
            print('  - ADD label "{}"'.format(name))
            if apply:
                repo.create_label(name=name, color=properties['color'],
                                  description=properties['description'])


def deploy_settings(repo, apply):
    update = False
    if repo.has_issues != True:
        print('  - CHANGE has_issues')
        update = True
    if repo.has_projects != False:
        print('  - CHANGE has_projects')
        update = True
    if repo.has_wiki != False:
        print('  - CHANGE has_wiki')
        update = True
    if repo.delete_branch_on_merge != True:
        print('  - CHANGE delete_branch_on_merge')
        update = True
    if repo.default_branch != 'master':
        print('  - CHANGE default_branch')
        update = True
    if update and apply:
        repo.edit(
            has_issues=True,
            has_projects=False,
            has_wiki=False,
            delete_branch_on_merge=True,
            default_branch='master',
        )


def deploy_branch_protection(repo, apply):
    update = False
    branch = repo.get_branch("master")
    if branch.protected != True:
        print('  - CHANGE protected')
        update = True
    if branch.protected:
        protection = branch.get_protection()
        if protection.enforce_admins != True:
            print('  - CHANGE enforce_admins')
            update = True
    if update and apply:
        branch.edit_protection(
            enforce_admins=True,
        )


def checkout(repo, branch_name):
    repo_dir = os.path.join(CACHE_DIR, repo.name)
    if not os.path.isdir(repo_dir):
        check_call(['git', 'clone', '-q', repo.ssh_url], cwd=CACHE_DIR)
    else:
        check_call(['git', 'reset', '-q', '--hard', 'master'], cwd=repo_dir)
        check_call(['git', 'clean', '-q', '-f', '-d', '-x'], cwd=repo_dir)
        check_call(['git', 'checkout', '-q', 'master'], cwd=repo_dir)
        check_call(['git', 'pull', '-q'], cwd=repo_dir)
    check_call(['git', 'checkout', '-q', '-B', branch_name], cwd=repo_dir)
    return repo_dir


def commit_local_changes(repo_dir, message):
    check_call(['git', 'add', '--all'], cwd=repo_dir)
    changes = check_output(['git', 'status', '--porcelain'], cwd=repo_dir).\
        decode('utf-8').strip()
    if len(changes) > 0:
        print('  ' + changes.replace('\n', '\n  '))
        check_call(['git', 'commit', '-q', '-m', message], cwd=repo_dir)
    return len(changes)


def upgrade_file_format(repo_dir, image_tag, commit_msg):
    lib_name = os.path.basename(repo_dir)
    check_call([
        'docker', 'run', '-i', '-t', '--rm',
        '-u', str(os.getuid()) + ':' + str(os.getgid()),
        '-v', str(repo_dir) + ':/work/' + lib_name,
        'librepcb/librepcb-cli:' + image_tag,
        'open-library', '--all', '--save', '/work/' + lib_name
    ])
    return commit_local_changes(repo_dir, commit_msg)


def update_files(repo_dir):
    copy_tree(FILES_DIR, repo_dir)
    return commit_local_changes(repo_dir, 'Update from template')

def deploy_local_changes(repo, repo_dir, branch_name, pr_title, changes, apply):
    pr_body = '*Automatically created pull request to update some files to ' \
              'their latest version from [librepcb-libraries-admin]' \
              '(https://github.com/LibrePCB/librepcb-libraries-admin).*'
    if (changes > 0) and apply:
        check_call(['git', 'push', '-q', '-f', 'origin', branch_name],
                    cwd=repo_dir)
    pr = repo.get_pulls(state='open', head='LibrePCB-Libraries:' + branch_name,
                        base='master')
    if (changes > 0) and (pr.totalCount == 0):
        print('  OPEN pull request')
        if apply:
            pr = repo.create_pull(title=pr_title, body=pr_body,
                                  head=branch_name, base='master')
            pr.add_to_labels('ready for review')


def deploy_repo(repo, upgrade_version, branch_name, pr_title, apply):
    print(repo.name + ':')
    deploy_labels(repo, apply)
    deploy_settings(repo, apply)
    deploy_branch_protection(repo, apply)

    changes = 0
    repo_dir = checkout(repo, branch_name)
    if upgrade_version:
        changes += upgrade_file_format(repo_dir, upgrade_version, pr_title)
    changes += update_files(repo_dir)
    deploy_local_changes(repo, repo_dir, branch_name, pr_title, changes, apply)


def deploy(config):
    gh = Github(config['--token'])
    org = gh.get_organization('LibrePCB-Libraries')
    upgrade_tag = config.get('--upgrade')
    if upgrade_tag:
        branch_name = 'upgrade-file-format'
        pr_title = 'Upgrade to file format v{}'.format(
            upgrade_tag.split('.')[0])
    else:
        branch_name = 'update-from-template'
        pr_title = "Update from template"

    libraries = config['<library>']
    for repo in org.get_repos():
        if (repo.name in libraries) or (not libraries):
            deploy_repo(repo, upgrade_tag, branch_name, pr_title,
                        config['--apply'])


if __name__ == '__main__':
    try:
        options = json.load(open('options.json', mode='r'))
    except:
        options = {}

    args = docopt(__doc__)
    config = dict((str(key), options.get(key) or args.get(key))
                  for key in set(args) | set(options))
    deploy(config)
