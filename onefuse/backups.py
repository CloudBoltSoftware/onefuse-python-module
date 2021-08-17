import json
import os
import sys
from os import listdir
from os.path import isfile, join
import errno

from onefuse.admin import OneFuseManager


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
    for specifics.

    Parameters
    ----------
    ofm : OneFuseManager

    Examples
    --------
    Create a connection to OneFuse and instantiate a BackupManager:
        from onefuse.admin import OneFuseManager
        from onefuse.backups import BackupManager
        ofm = OneFuseManager('username','password','onefuse_fqdn')
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
    """

    def __init__(self, ofm: OneFuseManager, **kwargs):
        self.ofm = ofm

    def __enter__(self):
        return self

    def __repr__(self):
        return 'OneFuseBackups'

    # Backups Content
    def create_json_files(self, response, policy_type, backups_path):
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
                raise Exception(error_string)
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
                raise Exception(error_string)
        response_json = response.json()

        for policy in response_json["_embedded"][policy_type]:
            self.ofm.logger.debug(f'Backing up {policy_type} policy: '
                                  f'{policy["name"]}')
            filename = f'{backups_path}{policy_type}{path_char}' \
                       f'{policy["name"]}'
            if policy_type == "endpoints":
                if "credential" in policy["_links"]:
                    policy["_links"]["credential"][
                        "title"] = self.get_credential_name(policy, self.ofm)
            if not os.path.exists(os.path.dirname(filename)):
                try:
                    os.makedirs(os.path.dirname(filename))
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

        return self.key_exists(response_json["_links"], "next")

    def get_credential_name(self, policy, onefuse):
        href = policy["_links"]["credential"]["href"]
        url = href.replace('/api/v3/onefuse', '')
        response = onefuse.get(url)
        try:
            response.raise_for_status()
        except:
            err_msg = f'Link could not be found for href: {href}'
            raise Exception(err_msg)
        self.ofm.logger.debug(f'Returning Credential name: '
                              f'{response.json()["name"]}')
        return response.json()["name"]

    def key_exists(self, in_dict, key):
        if key in in_dict.keys():
            self.ofm.logger.debug(f'Key exists: {key}')
            return True
        else:
            return False

    def backup_policies(self, backups_path):
        policy_types = [
            "moduleCredentials", "endpoints", "validators", "namingSequences",
            "namingPolicies", "propertySets", "ipamPolicies", "dnsPolicies",
            "microsoftADPolicies", "ansibleTowerPolicies",
            "scriptingPolicies", "servicenowCMDBPolicies", "vraPolicies"
        ]

        # Gather policies from OneFuse, store them under BACKUPS_PATH
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
                restore_json[key] = json_content[key]
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
            raise Exception(error_string)

    def restore_policies_from_file_path(self, file_path: str,
                                        overwrite: bool = False):
        """
        Restore all policies from a File Path. This file path needs to be
        local on the host where this script is being run from. The file
        structure should look like the following:

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
        """
        policy_types = [
            "moduleCredentials", "endpoints", "validators", "namingSequences",
            "namingPolicies", "propertySets", "ipamPolicies", "dnsPolicies",
            "microsoftADPolicies", "ansibleTowerPolicies", "scriptingPolicies",
            "servicenowCMDBPolicies", "vraPolicies"
        ]

        # Gather policies from FILE_PATH, restore them to OneFuse
        for policy_type in policy_types:
            self.ofm.logger.info(f'Restoring policy_type: {policy_type}')
            policy_type_path = f'{file_path}{policy_type}{path_char}'
            if os.path.exists(os.path.dirname(policy_type_path)):
                policy_files = [f for f in listdir(policy_type_path)
                                if isfile(join(policy_type_path, f))]
                for file_name in policy_files:

                    f = open(f'{policy_type_path}{file_name}', 'r')
                    content = f.read()
                    f.close()
                    json_content = json.loads(content)
                    policy_name = json_content["name"]

                    if "type" in json_content:
                        url = (
                            f'/{policy_type}/?filter=name.iexact:"'
                            f'{policy_name}";type.iexact:"'
                            f'{json_content["type"]}"')
                    elif "endpointType" in json_content:
                        url = (
                            f'/{policy_type}/?filter=name.iexact:"'
                            f'{policy_name}";endpointType.iexact:"'
                            f'{json_content["endpointType"]}"')
                    else:
                        url = f'/{policy_type}/?filter=name.iexact:"' \
                              f'{policy_name}"'
                    # Check does policy exist
                    response = self.ofm.get(url)
                    # self.ofm.logger.debug(f'url: {url}')
                    # Check for errors. If "Not Found." continue to next
                    # file_name
                    try:
                        response.raise_for_status()
                    except:
                        try:
                            detail = response.json()["detail"]
                        except:
                            error_string = (
                                f'Unknown error. JSON: {response.json()}, ')
                            error_string += (
                                f'Error: {sys.exc_info()[0]}. '
                                f'{sys.exc_info()[1]}, '
                                f'line: {sys.exc_info()[2].tb_lineno}')
                            raise Exception(error_string)
                        if detail == 'Not found.':
                            # This may happen when script is run against older
                            # versions of Onefuse that do not support all modules
                            self.ofm.logger.warning(
                                f'policy_type not found: {policy_type}, '
                                f'file_name: {file_name}')
                            continue
                        else:
                            error_string = (
                                f'Unknown error. JSON: {response.json()}, '
                                f'Error: {sys.exc_info()[0]}. '
                                f'{sys.exc_info()[1]}, '
                                f'line: {sys.exc_info()[2].tb_lineno}')
                            raise Exception(error_string)

                    response_json = response.json()
                    if response_json["count"] == 0:
                        self.ofm.logger.info(
                            f'Creating OneFuse Content. policy_type: '
                            f'{policy_type}, file_name: {file_name}')
                        url = f'/{policy_type}/'
                        restore_content = self.create_restore_content(
                            policy_type, json_content)
                        if policy_type == "moduleCredentials":
                            restore_content["password"] = "Pl@ceHolder123!"
                            self.ofm.logger.warning(
                                f'Your credential has been restored but '
                                f'before it can be used you must update the '
                                f'password for the credential: {file_name}')
                        response = self.ofm.post(url, json=restore_content)
                        try:
                            response.raise_for_status()
                        except:
                            error_string = (
                                f'Creation Failed. url: {url}, '
                                f'restore_content: {restore_content}'
                                f'Error: {response.content}')
                            raise Exception(error_string)

                    elif response_json["count"] == 1:
                        if overwrite:
                            self.ofm.logger.info(
                                f'Updating OneFuse Content. policy_type: '
                                f'{policy_type}, file_name: {file_name}')
                            policy_json = \
                                response_json["_embedded"][policy_type][0]
                            policy_id = policy_json["id"]
                            url = f'/{policy_type}/{policy_id}/'
                            restore_content = self.create_restore_content(
                                policy_type, json_content)
                            response = self.ofm.put(url, json=restore_content)
                            response.raise_for_status()
                        else:
                            self.ofm.logger.info(f'Overwrite is set to: '
                                                 f'{overwrite}, Policy: '
                                                 f'{policy_name} already '
                                                 f'exists. Skipping')
                    else:
                        warn_str = (
                            f'WARN: More than one policy was found with'
                            f' the name: {policy_name} and type: '
                            f'{policy_type}. Skipping policy restore')
                        self.ofm.logger.warning(warn_str)
            else:
                self.ofm.logger.info(
                    f'Directory for policy type: {policy_type} does not '
                    f'exist. Skipping.')
