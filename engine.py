import glob
import os
import subprocess
import logging
import json
from datetime import date, timedelta, datetime
import logging
import re

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
        nb_files = 0

        for calculated_item in calculated_list:  # on fait la somme de tous les enfants
            added_total += int(calculated_item.get('size'))

            if calculated_item.get('nb_files') != None:
                if calculated_item.get('type') != "dir":
                    nb_files += calculated_item.get('nb_files') + 1
                else:
                    nb_files += calculated_item.get('nb_files')
            else:
                if calculated_item.get('type') != "dir":
                    nb_files += 1

        object[data_parameter_name]['size'] = added_total
        object[data_parameter_name]['nb_files'] = nb_files

    return object.get(data_parameter_name)


def convert_path_in_object(data_object, single_line_object, repo, **kwargs):
    path = single_line_object.get('path')

    parts = [p for p in path.split('/') if p]

    new = kwargs.get('new', None)
    old = kwargs.get('old', None)

    converted = data_object
    path = ''
    for index, item in enumerate(parts):
        path = path + '/' + item
        converted = converted.setdefault(item, {'/info': {
            'name': single_line_object.get('name'),
            'type': single_line_object.get('type'),
            'path': single_line_object.get('path'),
            'mtime': single_line_object.get('mtime'),
            'size': single_line_object.get('size'),
            'hidden': is_hidden_path(single_line_object.get('path'), repo)
        }})

        if new is not None or old is not None:
            converted.get('/info')['size'] = None
            converted.get('/info')['mtime'] = None
            converted.get('/info')['name'] = item
            converted.get('/info')['path'] = path

            if index != parts.index(parts[-1]):
                converted.get('/info')['type'] = 'dir'

    if new is not None or old is not None:
        converted.get('/info')['modifier'] = kwargs.get('modifier')
        converted.get('/info')['old_size'] = None
        converted.get('/info')['old_mtime'] = None

    if new is not None and new != {}:
        converted.get('/info')['size'] = new.get('/info').get('size')
        converted.get('/info')['mtime'] = new.get('/info').get('mtime')

    if old is not None and old != {}:
        converted.get('/info')['old_size'] = old.get('/info').get('size')
        converted.get('/info')['old_mtime'] = old.get('/info').get('mtime')


def is_hidden_path(path, repo):
    try:
        for item in __pu.get('app').get('ignore_path'):
            if re.match(item, path):
                return True

        for item in __pu.get('repo').get(repo).get('ignore_path', []):
            if re.match(item, path):
                return True
    except re.PatternError as e:  # can fail with some strange file names like [
        pass

    return False


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
        command = ['./restic', '--repo', url, '--password-file', f'.secrets/{key}', 'snapshots', '--json']
        if item.get('tag', None) is not None:
            command.append('--tag')
            command.append(item.get('tag'))

        command_result = subprocess.run(
            command,
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
                convert_path_in_object(snapshot_data, json.loads(line.strip()), repo=repo)

        calculate_size(snapshot_data)
        final_object = snapshot_data.copy()
        remove_hidden(snapshot_data, final_object)
        cache_file = open(cache_filename, 'w')
        json.dump(final_object, cache_file)
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
                final_object = json.load(cache_file)
                cache_file.close()

                cache_file = open(f'{cache_filename}.metadata', 'r')
                metadata = json.load(cache_file)
                cache_file.close()
            except:
                logging.error('get_snapshot_files : Cannot use cache, trying without cache')
                return get_snapshot_files(repo=repo, snapshot_id=snapshot_id, ignore_cache=True)

    return metadata, final_object


def remove_hidden(object, final_object):
    data_parameter_name = '/info'

    hidden = object.get(data_parameter_name).get('hidden', False)
    for entry in object:
        if hidden is False:
            if entry != data_parameter_name and final_object is not None:
                remove_hidden(object.get(entry), final_object.get(entry, None))
        else:
            if entry != data_parameter_name:
                final_object[entry] = None
            else:
                final_object[data_parameter_name] = object.get(data_parameter_name).copy()


def get_diff(repo, snapshot1_id, snapshot2_id, force_refresh=False, ignore_cache=False):
    repos_list = __pu.get('repo')

    refresh_cache, cache_filename = check_if_cache_available(repo, f'{snapshot1_id}_{snapshot2_id}.diff')

    if refresh_cache or ignore_cache:
        if repos_list.get(repo, None) is None:
            return '{ "message_type": "exit_error", "message" : "Unknown repository" }', None

        command_result = subprocess.run(
            ['./restic', '--repo', repos_list[repo].get('url'), '--password-file', f'.secrets/{repo}', 'diff',
             snapshot2_id, snapshot1_id, '--json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        raw = command_result.stdout.split('\n')

        metadata1, result1 = get_snapshot_files(repo, snapshot1_id, False)
        metadata2, result2 = get_snapshot_files(repo, snapshot2_id, False)

        diff_object = {'/info': {'size': None, 'path': ''}}

        for diff in raw[0:-2]:
            item_obj = json.loads(diff)
            item_path = item_obj.get('path').split('/')[1:]

            print(item_obj)
            current_new = result1
            try:
                for key in item_path:
                    current_new = current_new.get(key, {})
                new = current_new
            except AttributeError:
                new = None

            current_old = result2
            try:
                for key in item_path:
                    current_old = current_old.get(key, {})

                old = current_old.copy()
            except AttributeError:
                old = None

            if current_new != {} and current_new is not None:
                convert_path_in_object(diff_object, new.get('/info'), repo, old=old, new=new,
                                       modifier=item_obj.get('modifier'))
            elif current_old != {} and current_old is not None:
                convert_path_in_object(diff_object, old.get('/info'), repo, old=old, new=new,
                                       modifier=item_obj.get('modifier'))

        calculate_diff_size(diff_object)

        cache_file = open(cache_filename, 'w')
        json.dump(diff_object, cache_file)
        cache_file.close()

        metadata_file = open(f'{cache_filename}.metadata', 'w')
        metadata = json.loads(raw[-2])
        json.dump(metadata, metadata_file)
        metadata_file.close()
        return metadata, diff_object
    else:
        if not ignore_cache:
            try:
                logging.info(f'Using cache file : {cache_filename}')

                cache_file = open(cache_filename, 'r')
                diff_object = json.load(cache_file)
                cache_file.close()

                cache_file = open(f'{cache_filename}.metadata', 'r')
                metadata = json.load(cache_file)
                cache_file.close()
                return metadata, diff_object
            except:
                logging.error('get_diff : Cannot use cache, trying without cache')
                return get_diff(repo=repo, snapshot1_id=snapshot1_id, snapshot2_id=snapshot2_id, ignore_cache=True)


def calculate_diff_size(object):
    data_parameter_name = '/info'

    if object.get(data_parameter_name).get('path') == '' or object.get(data_parameter_name).get(
            'type') == 'dir':  # si présent = c'est un fichier, sinon, c'est un répertoire avec des enfants
        calculated_list = []
        for entry in object:  # On récupère la valeur de tous les enfants
            if entry != data_parameter_name:
                results = calculate_diff_size(object.get(entry))
                calculated_list.append(results)

        total_added_size = 0
        total_removed_size = 0
        total_added_files = 0
        total_removed_files = 0
        total_changed_files = 0

        for calculated_item in calculated_list:  # on fait la somme de tous les enfants
            if calculated_item.get('modifier', None) == '-':
                total_removed_size = total_removed_size + calculated_item.get('old_size')
                total_removed_files = total_removed_files + 1
            elif calculated_item.get('modifier', None) == '+':
                total_added_size = total_added_size + calculated_item.get('size')
                total_added_files = total_added_files + 1
            elif calculated_item.get('modifier', None) == 'M':
                total_changed_files = total_changed_files + 1
                if calculated_item.get('old_size') > calculated_item.get('size'):
                    total_removed_size = total_removed_size + (
                            calculated_item.get('old_size') - calculated_item.get('size'))
                else:
                    total_added_size = total_added_size + (
                            calculated_item.get('size') - calculated_item.get('old_size'))
            if calculated_item.get('size') is None and calculated_item.get('old_size') is None:
                total_added_size = total_added_size + calculated_item.get('total_added_size', 0)
                total_removed_size = total_removed_size + calculated_item.get('total_removed_size', 0)
                total_added_files = total_added_files + calculated_item.get('total_added_files', 0)
                total_removed_files = total_removed_files + calculated_item.get('total_removed_files', 0)
                total_changed_files = total_changed_files + calculated_item.get('total_changed_files', 0)

        object[data_parameter_name]['total_added_size'] = total_added_size
        object[data_parameter_name]['total_removed_size'] = total_removed_size
        object[data_parameter_name]['total_added_files'] = total_added_files
        object[data_parameter_name]['total_removed_files'] = total_removed_files
        object[data_parameter_name]['total_changed_files'] = total_changed_files

    return object.get(data_parameter_name)
