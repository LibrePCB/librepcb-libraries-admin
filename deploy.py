#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Administrate LibrePCB Libraries

Usage:
  deploy.py [--token=<token>] [--single] [--apply]
  deploy.py (-h | --help)

Options:
  -h --help         Show this screen.
  --token=<token>   GitHub API token.
  --apply           Apply the required changes.
  --single          Only deploy to LibrePCB_Base.lplib (for testing purposes).

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
    if update and apply:
        repo.edit(has_issues=True, has_projects=False, has_wiki=False)


def deploy_files(repo, apply):
    branch_name = 'update-from-template'
    commit_msg = 'Update from template'
    pr_title = commit_msg
    pr_body = '**Automatically created pull request to update some files to ' \
              'their latest version from [librepcb-libraries-admin]' \
              '(https://github.com/LibrePCB/librepcb-libraries-admin).**'
    repo_dir = os.path.join(CACHE_DIR, repo.name)
    if not os.path.isdir(repo_dir):
        check_call(['git', 'clone', '-q', repo.ssh_url], cwd=CACHE_DIR)
    else:
        check_call(['git', 'reset', '-q', '--hard', 'master'], cwd=repo_dir)
        check_call(['git', 'clean', '-q', '-f', '-d', '-x'], cwd=repo_dir)
        check_call(['git', 'checkout', '-q', 'master'], cwd=repo_dir)
        check_call(['git', 'pull', '-q'], cwd=repo_dir)
    check_call(['git', 'checkout', '-q', '-B', branch_name], cwd=repo_dir)
    copy_tree(FILES_DIR, repo_dir)
    check_call(['git', 'add', '--all'], cwd=repo_dir)
    changes = check_output(['git', 'status', '--porcelain'], cwd=repo_dir).\
        decode('utf-8').strip()
    if len(changes) > 0:
        print('  ' + changes.replace('\n', '\n  '))
        check_call(['git', 'commit', '-q', '-m', commit_msg], cwd=repo_dir)
        if apply:
            check_call(['git', 'push', '-q', '-f', 'origin', branch_name],
                       cwd=repo_dir)
    pr = repo.get_pulls(state='open', head='LibrePCB-Libraries:' + branch_name,
                        base='master')
    if (pr.totalCount == 0) and apply:
        pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name,
                              base='master')
        pr.add_to_labels('ready for review')


def deploy_repo(repo, apply):
    print(repo.name + ':')
    deploy_labels(repo, apply)
    deploy_settings(repo, apply)
    deploy_files(repo, apply)


def deploy(config):
    gh = Github(config['--token'])
    org = gh.get_organization('LibrePCB-Libraries')
    for repo in org.get_repos():
        if (repo.name == 'LibrePCB_Base.lplib') or not config['--single']:
            deploy_repo(repo, config['--apply'])


if __name__ == '__main__':
    try:
        options = json.load(open('options.json', mode='r'))
    except:
        options = {}

    args = docopt(__doc__)
    config = dict((str(key), options.get(key) or args.get(key))
                  for key in set(args) | set(options))
    deploy(config)
