#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Administrate LibrePCB Libraries

Usage:
  deploy.py [--token=<token>] [--apply]
  deploy.py (-h | --help)

Options:
  -h --help         Show this screen.
  --token=<token>   GitHub API token.
  --apply           Apply the required changes.

"""
from docopt import docopt
from github import Github, Label
import json


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


def deploy_repo(repo, apply):
    print(repo.name + ':')
    deploy_labels(repo, apply)
    deploy_settings(repo, apply)


def deploy(config):
    gh = Github(config['--token'])
    org = gh.get_organization('LibrePCB-Libraries')
    for repo in org.get_repos():
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
