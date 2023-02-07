import json
import os
import sys
from os import listdir
from os.path import isfile, join
import errno
from .exceptions import (BackupsUnknownError, RestoreContentError,
                         OneFuseError, PolicyTypeNotFound)
from .admin import OneFuseManager
from requests.exceptions import HTTPError
from packaging import version


# If system run on is Windows, swap '/' with '\\' for file paths
if os.name == 'nt':
    path_char = '\\'
else:
    path_char = '/'


class BackupManager(object):
    """
    A class used to facilitate easy OneFuse Backups and Restores. This class
    considers the differences in Linux and Windows file paths and when calling
    each method, depending on the OS this is being called from the file path
    passed in to the methods will need to be slightly different. See examples
    for specifics. Will create a file structure similar to the following

    file_path
    |--- microsoftADPolicies
    |    |--- production.json
    |--- endpoints
    |    |--- cloudbolt_io.json

    Parameters
    ----------
    ofm : OneFuseManager

    Examples
    --------
    Create a connection to OneFuse and instantiate a BackupManager:
        from onefuse.admin import OneFuseManager
        from onefuse.backups import BackupManager
        ofm = OneFuseManager('username','password','onefuse_fqdn',
                             log_level='INFO')
        backups = BackupManager(ofm)

    Backup all OneFuse policies to a file path on Linux
        backups.backup_policies('/file_path/')

    Backup all OneFuse policies to a file path on Windows. All backslashes need
    To be double to prevent escaping the string.
        backups.backup_policies('C:\\temp\\onefuse_backups\\')

    Restore all OneFuse policies found in a file path to OneFuse - Linux
        backups.restore_policies_from_file_path('/file_path/')

    Restore all OneFuse policies found in a file path to OneFuse - Windows
        backups.restore_policies_from_file_path('C:\\temp\\onefuse_backups\\')

    Restore a single OneFuse policy from json file (Windows) -
        backups.restore_single_policy(
                'C:\\temp\\onefuse_backups\\propertySets\\static_prod.json')
    """

    def __init__(self, ofm: OneFuseManager, **kwargs):
        self.ofm = ofm
        self.policy_types = [
            "moduleCredentials", "endpoints", "validators", "namingSequences",
            "namingPolicies", "propertySets", "ipamPolicies", "dnsPolicies",
            "microsoftADPolicies", "ansibleTowerPolicies", "scriptingPolicies",
            "servicenowCMDBPolicies", "vraPolicies"
        ]

        if version.parse(self.ofm.onefuse_version) >= version.parse('1.4'):
            self.policy_types.insert(0, 'modules')
            self.policy_types.insert(1, 'connectionInfo')
            self.policy_types.append('modulePolicies')

    def __enter__(self):
        return self

    def __repr__(self):
        return 'OneFuseBackups'

    # Backups Content
    def create_json_files(self, response, policy_type: str, backups_path: str):
        """
        Creates the json files and stores them in backups_path for the OneFuse
        policies being backed up. For single policy backups returns None,

        Parameters
        ----------
        response : requests.models.Response OR dict
            The response from a OneFuse call to get OneFuse policies. If a
            dict is passed in that would be a single OneFuse policy, if it is
            the Response type that would be the actual Response from a list
            query against a OneFuse type
        policy_type : str
            The type of policy being backed up, used to create sub directories
            when storing the files
        backups_path : str
            The file path where the json files should be stored
        """
        if type(response) == dict:
            # if a dict was passed in it was for the single policy backup,
            # Need to structure as a list
            policies = [response]
        else:
            try:
                response.raise_for_status()
            except:
                try:
                    detail = response.json()["detail"]
                except:
                    error_string = f'Unknown error. JSON: {response.json()}, '
                    error_string += (
                        f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                        f'line: {sys.exc_info()[2].tb_lineno}')
                    raise
                if detail == 'Not found.':
                    # This may happen when script is run against older versions.
                    self.ofm.logger.warning(f"policy_type not found: "
                                            f"{policy_type}")
                    return False
                else:
                    error_string = f'Unknown error. JSON: {response.json()}, '
                    error_string += (
                        f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                        f'line: {sys.exc_info()[2].tb_lineno}')
                    raise OneFuseError(error_string, response=response)
            response_json = response.json()
            policies = response_json["_embedded"][policy_type]

        for policy in policies:
            self.ofm.logger.debug(f'Backing up {policy_type} policy: '
                                  f'{policy["name"]}')
            file_path = f'{backups_path}{policy_type}{path_char}'
            if policy_type == 'modules':
                # Modules will overwrite existing modules in the file path if
                # found
                self.ofm.export_pluggable_module(policy["name"], file_path,
                                                 True)
                continue
            if policy_type == "endpoints":
                if "credential" in policy["_links"]:
                    # OneFuse 1.2 had a bug where the title of a credential
                    # Started with 'Module Credential id', if that is the
                    # case we will grab the actual credential title from the
                    # system
                    if (policy["_links"]["credential"]["title"].find(
                            "Module Credential id") == 0):
                        policy["_links"]["credential"][
                            "title"] = self.get_credential_name(policy)
            if not os.path.exists(os.path.dirname(file_path)):
                try:
                    os.makedirs(os.path.dirname(file_path))
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            if "type" in policy:
                file_name = f'{backups_path}{policy_type}{path_char}' \
                            f'{policy["type"]}_{policy["name"]}.json'
            elif "endpointType" in policy:
                file_name = f'{backups_path}{policy_type}{path_char}' \
                            f'{policy["endpointType"]}_{policy["name"]}.json'
            else:
                file_name = f'{backups_path}{policy_type}{path_char}' \
                            f'{policy["name"]}.json'
            f = open(file_name, 'w+')
            f.write(json.dumps(policy, indent=4))
            f.close()
        if type(response) == dict:
            # When running a single policy backup, None should be returned
            return None

        return self.key_exists(response_json["_links"], "next")

    def get_credential_name(self, policy: dict):
        """
        Returns the name of a OneFuse Credential from an endpoint policy

        Parameters
        __________
        policy : dict
            The dict of an endpoint policy
        """
        href = policy["_links"]["credential"]["href"]
        url = href.replace('/api/v3/onefuse', '')
        response = self.ofm.get(url)
        try:
            response.raise_for_status()
        except:
            err_msg = f'Link could not be found for href: {href}'
            raise OneFuseError(err_msg)
        self.ofm.logger.debug(f'Returning Credential name: '
                              f'{response.json()["name"]}')
        return response.json()["name"]

    def key_exists(self, in_dict: dict, key: str):
        """
        Returns a boolean indicating whether a key exists in a dict

        Parameters
        ----------
        in_dict : dict
            Dict to check for existence of key
        key : str
            Key to check for
        """
        if key in in_dict.keys():
            self.ofm.logger.debug(f'Key exists: {key}')
            return True
        else:
            return False

    def backup_policies(self, backups_path: str, type: str = None):
        """
        Back up all OneFuse policies from the OneFuse instance used when
        instantiating the OneFuseBackups class

        Parameters
        ----------
        backups_path : str
            Path to back the files up to. Examples:
                Windows: 'C:\\temp\\onefuse_backups\\'
                Linux: '/tmp/onefuse_backups/'
        type: str
            Optional type. Will backup all "policies" of the given type
            or raise an error if the parameter passed is not valid.
        """
        # Gather policies from OneFuse, store them under BACKUPS_PATH
        policy_types = self.policy_types
        if type:
            if type in policy_types:
                policy_types = [type]
            else:
                error_string = (
                    f"Type not found. Type '{type}' should be oe of {policy_types}"
                )
                raise OneFuseError(error_string)
        for policy_type in policy_types:
            self.ofm.logger.info(f'Backing up policy_type: {policy_type}')
            response = self.ofm.get(f'/{policy_type}/')
            next_exists = self.create_json_files(response, policy_type,
                                                 backups_path)
            while next_exists:
                next_page = response.json()["_links"]["next"]["href"]
                next_page = next_page.split("/?")[1]
                response = self.ofm.get(f'/{policy_type}/?{next_page}')
                next_exists = self.create_json_files(response, policy_type,
                                                     backups_path)

    def backup_single_policy(self, backups_path: str, policy_type: str,
                             policy_name: str):
        """
        Back up a single OneFuse policy by name. Note: using this method will
        not capture any linked policies, only the single policy requested
        without any dependencies. The backed up policy will be placed in the
        backups_path specified under a directory matching the policy_type

        Parameters
        ----------
        backups_path : str
            Path to back the files up to. Examples:
                Windows: 'C:\\temp\\onefuse_backups\\'
                Linux: '/tmp/onefuse_backups/'
        policy_type : str
            The type of policy to backup. Ex. 'namingPolicies'
        policy_name : str
            Name of the policy to backup. Ex: 'production'
        """
        self.ofm.logger.info(f'Backing up policy_type: {policy_type}, '
                             f'policy_name: {policy_name}')

        response = self.ofm.get_policy_by_name(policy_type, policy_name)
        self.create_json_files(response, policy_type, backups_path)

    # Restore Content
    def create_restore_content(self, policy_type: str, json_content: dict):
        """
        Creates and returns a dict for restoration of a policy in any instance
        of OneFuse. In different instances, endpoints (for example) may have
        the same name but a different ID.

        Parameters
        ----------
        policy_type : str
            Type of policy the link is used for. Ex: 'microsoftADPolicies'
        json_content : dict
            Dict of JSON of a policy that you are looking to restore
        """
        restore_json = {}
        for key in json_content:
            if key == "_links":
                for key2 in json_content["_links"]:
                    if key2 != "self":
                        if isinstance(json_content["_links"][key2], dict):
                            href = json_content["_links"][key2]["href"]
                            link_name = json_content["_links"][key2]["title"]
                            link_type = href.replace('/api/v3/onefuse', '')
                            link_type = link_type.split('/')[1]
                            link_id = self.get_link_id(link_type,
                                                       link_name,
                                                       policy_type,
                                                       json_content)
                            restore_json[key2] = link_id
                        elif isinstance(json_content["_links"][key2], list):
                            restore_json[key2] = []
                            for link in json_content["_links"][key2]:
                                href = link["href"]
                                link_name = link["title"]
                                link_type = href.replace('/api/v3/onefuse', '')
                                link_type = link_type.split('/')[1]
                                link_id = self.get_link_id(link_type,
                                                           link_name,
                                                           policy_type,
                                                           json_content)
                                restore_json[key2].append(link_id)
                        else:
                            self.ofm.logger.warning(f'Unknown type found: '
                                                    f'{type(json_content["_links"][key2])}')
            elif key != 'id' and key != 'microsoftEndpoint':
                if policy_type == "namingSequences" and key == "lastValue":
                    if json_content[key] is None:
                        restore_json[key] = "1"
                    else:
                        restore_json[key] = json_content[key]
                elif policy_type == "endpoints" and (
                        key.find('Version') != -1
                        or key.find('version') != -1):
                    # If policy_type is endpoints, need to remove version info
                    # when restoring from older versions to 1.4+
                    if version.parse(self.ofm.onefuse_version) < version.parse('1.4'):
                        restore_json[key] = json_content[key]
                elif policy_type == "propertySets" and key == "type":
                    # OneFuse 1.4+ no longer has the type key on a Property set
                    if version.parse(self.ofm.onefuse_version) < version.parse('1.4'):
                        restore_json[key] = json_content[key]
                else:
                    restore_json[key] = json_content[key]

        if policy_type == 'ipamPolicies' and \
            version.parse(self.ofm.onefuse_version) >= version.parse('1.4'):
            # If restoring from < 1.3 to 1.4, need to add skip IP defaults
            if "updateConflictNameWithDns" not in restore_json:
                restore_json["updateConflictNameWithDns"] = False
        print(f"restore_json: {restore_json}")
        return restore_json

    def get_link_id(self, link_type: str, link_name: str, policy_type: str,
                    json_content: dict):
        """
        Return the link ID for OneFuse elements. Used when reconstructing the
        JSON content for restoring policies to a OneFuse instance that is not
        the original instance the policies were backed up from. This will find
        and return a link of a certain type based off of the name of the link
        and the policy type that the link is used for.

        Parameters
        ----------
        link_type : str
            Type of link. Ex: 'workspaces', or 'endpoints'
        link_name : str
            Name of the link to return. Ex: 'cloudbolt_io'
        policy_type : str
            Type of policy the link is used for. Ex: 'microsoftADPolicies'
        json_content : dict
            Dict of JSON of a policy that you are looking to restore
        """
        if link_type == 'endpoints':
            if policy_type == "microsoftADPolicies":
                endpoint_type = "microsoft"
            elif policy_type == "ansibleTowerPolicies":
                endpoint_type = "ansible_tower"
            elif policy_type == "servicenowCMDBPolicies":
                endpoint_type = "servicenow"
            else:
                endpoint_type = json_content["type"]
            url = (f'/{link_type}/?filter=name.iexact:"{link_name}";'
                   f'type.iexact:"{endpoint_type}"')
        else:
            url = f'/{link_type}/?filter=name.iexact:"{link_name}"'
        link_response = self.ofm.get(url)
        link_response.raise_for_status()
        link_json = link_response.json()
        if link_json["count"] == 1:
            return link_json["_embedded"][link_type][0]["_links"]["self"][
                "href"]
        else:
            error_string = (f'Link not found. link_type: {link_type}'
                            f'link_name: {link_name}')
            raise OneFuseError(error_string)

    def restore_policies_from_file_path(self, file_path: str,
                                        overwrite: bool = False,
                                        continue_on_error: bool = False):
        """
        Restore all policies from a File Path. This file path needs to be
        local on the host where this script is being run from. Default behavior
        of this method is to not overwrite policies that already exist and to
        not continue if there is an error with restoring any single policy.
        The file structure should look like the following:

        file_path
        |--- microsoftADPolicies
        |    |--- production.json
        |--- endpoints
        |    |--- cloudbolt_io.json

        Parameters
        ----------
        file_path : str
            Path to the directory housing the onefuse backups. Linux example:
            '/var/opt/cloudbolt/proserv/onefuse-backups/'
            Windows example:
            'C:\\temp\\onefuse_backups\\'
        overwrite : bool - optional
            Specify whether to overwrite existing policies with the data from
            the backup (True) even if the policy already exists, or to skip if
            the policy already exists (False). Defaults to False
        continue_on_error : bool - optional
            Continue to next policy if restore of a single policy fails?
            Default - False
        """
        # Gather policies from FILE_PATH, restore them to OneFuse
        for policy_type in self.policy_types:
            if policy_type == 'modules':
                self.ofm.logger.info("Modules cannot be restored using this"
                                     "method. While the OneFuse Backups module"
                                     " does back up OneFuse pluggable modules,"
                                     " these will need to be restored manually"
                                     " using the "
                                     "OneFuseManager.upload_pluggable_module"
                                     "method")
                continue
            else:
                self.ofm.logger.info(f'Restoring policy_type: {policy_type}')
                policy_type_path = f'{file_path}{policy_type}{path_char}'
                if os.path.exists(os.path.dirname(policy_type_path)):
                    policy_files = [f for f in listdir(policy_type_path)
                                    if isfile(join(policy_type_path, f))]
                    for file_name in policy_files:
                        json_path = f'{policy_type_path}{file_name}'
                        try:
                            self.restore_single_policy(json_path, overwrite)
                        except PolicyTypeNotFound:
                            continue
                        except Exception as err:
                            if continue_on_error:
                                err_str = f'Error encountered when restoring' \
                                          f' policy_type: {policy_type}, ' \
                                          f'file_name: {file_name}, but ' \
                                          f'continue_on_error is True, ' \
                                          f'continuing.'
                                self.ofm.logger.info(err_str)
                                continue
                            raise

    def restore_single_policy(self, json_path: str, overwrite: bool = False):
        """
        Restore a single OneFuse policy from a file. This method assumes that
        any linked policies referenced have already been restored

        Parameters
        ----------
        json_path : str
            Path to the single file that you want to restore. This file must
            be included under a directory that matches the policy type.
            Linux example:
            '/tmp/onefuse-backups/namingPolicies/prod.json'
            Windows example:
            'C:\\temp\\onefuse_backups\\namingPolicies\\prod.json'
        overwrite : bool - optional
            Specify whether to overwrite an existing policy with the data from
            the backup (True) even if the policy already exists, or to skip if
            the policy already exists (False). Defaults to False
        """
        path_split = json_path.split(path_char)
        policy_type = path_split[-2]
        file_name = path_split[-1]
        f = open(json_path, 'r')
        content = f.read()
        f.close()
        json_content = json.loads(content)
        policy_name = json_content["name"]

        if "type" in json_content and policy_type != "propertySets":
            url = (f'/{policy_type}/?filter=name.iexact:"'
                   f'{policy_name}";type.iexact:"'
                   f'{json_content["type"]}"')
        elif "endpointType" in json_content:
            url = (f'/{policy_type}/?filter=name.iexact:"'
                   f'{policy_name}";endpointType.iexact:"'
                   f'{json_content["endpointType"]}"')
        else:
            url = f'/{policy_type}/?filter=name.iexact:"' \
                  f'{policy_name}"'

        # Check does policy exist
        response = self.ofm.get(url)
        # Check for errors. If "Not Found." continue to next
        try:
            response.raise_for_status()
        except:
            try:
                detail = response.json()["detail"]
            except:
                self.ofm.logger.error('Response JSON detail cannot be '
                                      f'accessed. response: {response}')
                raise
            if detail == 'Not found.':
                # This may happen when script is run against older
                # versions of Onefuse that do not support all modules
                warn_msg = (
                    f'policy_type not found in OneFuse: {policy_type}, '
                    f'file_name: {file_name}')
                self.ofm.logger.warning(warn_msg)
                raise PolicyTypeNotFound(warn_msg)
            else:
                raise BackupsUnknownError(f'Request to URL: {url} '
                                          f'failed',
                                          response=response)
        response_json = response.json()

        if response_json["count"] == 0:
            self.ofm.logger.info(
                f'Creating OneFuse Content. policy_type: '
                f'{policy_type}, file_name: {file_name}')
            url = f'/{policy_type}/'
            try:
                restore_content = self.create_restore_content(
                    policy_type, json_content)
            except:
                self.ofm.logger.error(f'Restore content could not be '
                                      f'created for {file_name}.')
                raise
            if policy_type == "moduleCredentials":
                restore_content["password"] = "Pl@ceHolder123!"
                self.ofm.logger.warning(
                    f'Your credential has been restored but '
                    f'before it can be used you must update the '
                    f'password for the credential: {file_name}')
            try:
                response = self.ofm.post(url, json=restore_content)
                response.raise_for_status()
            except HTTPError:
                raise
            except Exception as err:
                err_msg = f'{err}. '
                err_msg += (f'Creation Failed for url: {url}, restore_content:'
                            f' {restore_content} Error: {response.content}.')
                self.ofm.logger.error(err_msg)
                raise

        elif response_json["count"] == 1:
            if overwrite:
                self.ofm.logger.info(f'Updating OneFuse Content. policy_type: '
                                     f'{policy_type}, file_name: {file_name}')
                policy_json = response_json["_embedded"][policy_type][0]
                policy_id = policy_json["id"]
                url = f'/{policy_type}/{policy_id}/'
                restore_content = self.create_restore_content(policy_type,
                                                              json_content)
                try:
                    response = self.ofm.put(url, json=restore_content)
                    response.raise_for_status()
                except HTTPError:
                    raise
                except Exception as err:
                    err_msg = f'{err}. '
                    err_msg += (f'Creation Failed for url: {url}, '
                                f'restore_content: {restore_content}. '
                                f'Error: {response.content}.')
                    self.ofm.logger.error(err_msg)
                    raise
            else:
                self.ofm.logger.warn(f'Overwrite is set to: {overwrite}, '
                                     f'Policy: {policy_name} already exists. '
                                     f'Skipping')
