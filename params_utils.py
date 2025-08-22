import configparser
import copy
import logging

from logger_utils import LoggingManager

default_params = {
    "app": {
        'listen_port': 8000,
        'listen_host': '0.0.0.0',
        'log_level': 'INFO',
        'logs_rotation': 7,
        'restic_executable_path' : 'restic',
        'backup_mountpoint' : '/backup',

        'snapshots_list_cache_file_retention': 24,
        'snapshot_cache_file_retention': 72,
    },

}

params_metadata = {
    'int': ['listen_port' 'logs_rotation', 'snapshots_list_cache_file_retention', 'snapshot_cache_file_retention'],
    'array': [],
    'cannot_be_none': {"repo:" : ['url', 'password']},
    'fixed_values': {},
    'censored_fields' : ['password']
}

def censor_parameters(data):
    censored = data
    for parameter in params_metadata.get('censored_fields'):
        for (key, item) in censored.items():
            if key == parameter:
                censored[key] = None

            if type(item) is dict:
                censor_parameters(item)

class ConfigManager:
    __parameters = {}
    __parameters_censored = {}

    def __init__(self):
        self.__app_config = configparser.ConfigParser(interpolation=None)

        try:
            self.__app_config.read('params/params.ini')
        except configparser.DuplicateSectionError as e:
            logging.critical(e)
            exit(1)

        self.__lu = LoggingManager()
        self.__log = self.__lu.get()

        self.__parse_parameters()

        self.__parameters_censored = copy.deepcopy(self.__parameters)
        censor_parameters(self.__parameters_censored)

    def __parse_parameters(self):
        for section in self.__app_config.sections():
            config_file_section = section

            splitted_section = section.split(':')

            if len(splitted_section) == 1:
                meta_index = section
                section_parameters = self.__parameters

            else:
                meta_index = f"{splitted_section[0]}:"
                section_parameters = self.__parameters.setdefault(splitted_section[0], {})
                section = ':'.join(splitted_section[1:])

            local_default_params=default_params.get(meta_index, {})
            cannot_be_none=params_metadata.get('cannot_be_none').get(meta_index, [])
            fixed_values=params_metadata.get('fixed_values').get(meta_index, [])

            for option in self.__app_config[config_file_section]:
                if option in params_metadata.get('int'):
                    try:
                        section_parameters.setdefault(section, {})[option] = self.__app_config.getint(section=config_file_section,
                                                                                                      option=option)
                    except ValueError:
                        self.get_logger().error(
                            f'params.ini [{config_file_section}] : Value {option} must be an integer, using default value ({local_default_params.get(option)}) instead')
                elif option in params_metadata.get('array'):
                    section_parameters.setdefault(section, {})[option] = self.__app_config.get(section=config_file_section,
                                                                                               option=option).split(',')
                else:
                    section_parameters.setdefault(section, {})[option] = self.__app_config.get(section=config_file_section,
                                                                                               option=option)

            section_parameters[section] = local_default_params | section_parameters.get(section)

            for param in cannot_be_none:
                if section_parameters.get(section).get(param, '') == '':
                    self.get_logger().fatal(
                        f'params.ini [{config_file_section}] : Values {cannot_be_none} cannot be None or empty')
                    exit(1)

            for param in fixed_values:
                if section_parameters.get(section).get(param, '') not in fixed_values.get(param):
                    self.get_logger().error(
                        f'params.ini [{config_file_section}] : {param} must be on those values : {fixed_values.get(param)}, found "{section_parameters.get(section).get(param)}", fallback to default value : {local_default_params.get(param)}')
                    section_parameters.get(section)[param] = local_default_params.get(param)

            if self.__parameters.get('app', None) is None:
                self.__parameters['app'] = default_params.get('app')

        self.__lu.set_log_level(self.get('app').get('log_level'))
        self.__lu.set_logs_rotation(self.get('app').get('logs_rotation'))

    def get(self, parameter):
        return self.__parameters.get(parameter)

    def get_all(self):
        return self.__parameters

    def get_all_censored(self):
        return self.__parameters_censored

    def get_logger(self):
        return self.__log

    @staticmethod
    def get_metadata():
        return params_metadata

    @staticmethod
    def get_defaults():
        return default_params

