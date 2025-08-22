import glob
import os
import subprocess
import logging
import json
from datetime import date, timedelta, datetime
import logging

import params_utils

__pu = params_utils.ConfigManager()


def is_cache_too_old(target_file, retention=__pu.get('app').get('snapshots_list_cache_file_retention')):
    try:
        file_info = os.stat(target_file)
    except FileNotFoundError as e:
        return True

    return datetime.fromtimestamp(file_info.st_ctime) < (datetime.today() - timedelta(hours=retention))


def clear_cache():
    file_list = glob.glob('.cache/*/*')
    for file in file_list:
        if is_cache_too_old(file, retention=__pu.get('app').get('snapshot_cache_file_retention')):
            logging.info(f'Delete outdated cache file : {file}')
            os.remove(file)


def check_if_cache_available(repo, file):
    target_file = f'.cache/{repo}/{file}'

    refresh_cache = False

    if is_cache_too_old(target_file):
        refresh_cache = True

        logging.info(f'No cache file found : {target_file}')

        try:
            os.makedirs('/'.join(target_file.split('/')[0:-1]))
        except FileExistsError as e:
            pass

    return refresh_cache, target_file


def calculate_size(object):
    data_parameter_name = '/info'

    if object.get(data_parameter_name).get(
            'size') == None:  # si présent = c'est un fichier, sinon, c'est un répertoire avec des enfants
        calculated_list = []
        for entry in object:  # On récupère la valeur de tous les enfants
            if entry != data_parameter_name:
                results = calculate_size(object.get(entry))
                calculated_list.append(results)

        added_total = 0

        for calculated_item in calculated_list:  # on fait la somme de tous les enfants
            added_total += int(calculated_item.get('size'))

        object[data_parameter_name]['size'] = added_total

    return object.get(data_parameter_name)


def convert_path_in_object(data_object, single_line_object):
    path = single_line_object.get('path')

    parts = [p for p in path.split('/') if p]

    converted = data_object
    for item in parts:
        converted = converted.setdefault(item, {'/info': {
            'name': single_line_object.get('name'),
            'type': single_line_object.get('type'),
            'path': single_line_object.get('path'),
            'mtime': single_line_object.get('mtime'),
            'size': single_line_object.get('size'),
        }})


def generate_secret_files():
    for repo, params in __pu.get_all().get('repo').items():
        secret_file = open(f'.secrets/{repo}', 'w')
        secret_file.write(params.get('password'))
        secret_file.close()


def get_all_snapshots(ignore_cache=False):
    snapshots = {}

    repos_list = __pu.get('repo')

    for repo in repos_list.items():
        key = repo[0]
        repo_object = repo[1]

        try:
            repo_object.pop('password')
        except KeyError:
            pass

        try:
            error, data = get_all_snapshots_for_repo(repo=repo, ignore_cache=ignore_cache)
            snapshots.setdefault(key, {'params': repo_object})['snapshots'] = data

            if error is None:
                repo_object['cache_date'] = os.stat(f'.cache/{key}/snapshots').st_ctime
            else:
                repo_object['error'] = json.loads(error)

        except:
            if not ignore_cache:
                clear_cache()
                logging.error(f'Cannot use cache file for {key}, trying without cache')
                try:
                    error, data = get_all_snapshots_for_repo(repo=repo, ignore_cache=True)
                    snapshots.setdefault(key, {'params': repo_object})['snapshots'] = data

                    if error is None:
                        repo_object['cache_date'] = os.stat(f'.cache/{key}/snapshots').st_ctime
                    else:
                        repo_object['error'] = json.loads(error)
                except:
                    logging.critical(f'Snapshots informations recovery for {key} failed')
            else:
                logging.critical(f'Snapshots informations recovery for {key} failed')

    return snapshots


def get_all_snapshots_for_repo(repo, ignore_cache=False):
    key, item = repo
    url = item.get('url')

    refresh_cache, cache_filename = check_if_cache_available(key, 'snapshots')

    if refresh_cache or ignore_cache:
        command_result = subprocess.run(
            ['./restic', '--repo', url, '--password-file', f'.secrets/{key}', 'snapshots', '--json'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if command_result.returncode != 0:
            logging.critical(command_result.stderr.strip())
            return command_result.stderr.strip(), None

        cache_file = open(cache_filename, 'w')
        data = json.loads(command_result.stdout)
        json.dump(data, cache_file)
        cache_file.close()
    else:
        cache_file = open(cache_filename, 'r')
        data = json.load(cache_file)
        cache_file.close()

        logging.info(f'GET ALL SNAPSHOTS FOR REPO [{key}] - Using cache file : {cache_filename}')

    return None, data


def get_snapshot_files(repo, snapshot_id, ignore_cache=False):
    metadata = None
    snapshot_data = None

    repos_list = __pu.get('repo')

    if repos_list.get(repo, None) is None:
        return '{ "message_type": "exit_error", "message" : "Unknown repository" }', None

    refresh_cache, cache_filename = check_if_cache_available(repo, snapshot_id)
    if refresh_cache or ignore_cache:
        snapshot_data = {'/info': {'size': None, 'path': ''}}

        command_result = subprocess.run(
            ['./restic', '--repo', repos_list[repo].get('url'), '--password-file', f'.secrets/{repo}', 'ls',
             snapshot_id, '--json', '--long'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        raw = command_result.stdout.split('\n')

        if command_result.returncode != 0:
            logging.critical(command_result.stderr.strip())
            return command_result.stderr.strip(), None

        for line in raw[1:-1]:  # The fist line is a summary
            if line != '':
                convert_path_in_object(snapshot_data, json.loads(line.strip()))

        calculate_size(snapshot_data)
        cache_file = open(cache_filename, 'w')
        json.dump(snapshot_data, cache_file)
        cache_file.close()

        metadata_file = open(f'{cache_filename}.metadata', 'w')
        metadata = json.loads(raw[0])
        json.dump(metadata, metadata_file)
        metadata_file.close()
    else:
        if not ignore_cache:
            try:
                logging.info(f'Using cache file : {cache_filename}')

                cache_file = open(cache_filename, 'r')
                snapshot_data = json.load(cache_file)
                cache_file.close()

                cache_file = open(f'{cache_filename}.metadata', 'r')
                metadata = json.load(cache_file)
                cache_file.close()
            except:
                logging.error('get_snapshot_files : Cannot use cache, trying without cache')
                return get_snapshot_files(repo=repo, snapshot_id=snapshot_id, ignore_cache=True)

    return metadata, snapshot_data
