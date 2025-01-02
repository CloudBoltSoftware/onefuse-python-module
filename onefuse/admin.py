import errno
import re
import sys
import json
import os
import requests
import socket
import logging
from typing import List
from requests.auth import HTTPBasicAuth
from os import path
from uuid import uuid1
from requests.exceptions import HTTPError
from .exceptions import (BackupsUnknownError, RestoreContentError,
                         OneFuseError, BadRequest, RequiredParameterMissing)

ROOT_PATH = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
sys.path.append(ROOT_PATH)
PROPERTY_SET_PREFIX = 'OneFuse_SPS_'


# noinspection DuplicatedCode,PyBroadException,PyShadowingNames
class OneFuseManager(object):
    """
    This is a context manager class available to Python that facilitates
    easy API connectivity from a Python script host to a OneFuse host.

    Example 1 - Make custom REST calls to OneFuse:
        from onefuse.admin import OneFuseManager
        ofm = OneFuseManager(username, password, host)
        response = ofm.get("/namingPolicies/")

    Example 2 - Provision Naming with OOB methods:
        from onefuse.admin import OneFuseManager
        ofm = OneFuseManager(username, password, host)
        naming_json = ofm.provision_naming(self, policy_name,
                                           template_properties, tracking_id)

    Authentication, headers, and url creation is handled within this class,
    freeing the caller from having to deal with these tasks.
    """

    def __init__(self, username: str, password: str, host: str, **kwargs):
        """
        Instantiate the OneFuseManager

        Parameters
        ----------
        username : str
            OneFuse username
        password : str
            OneFuse password
        host : str
            OneFuse host FQDN. Ex: 'onefuse.cloudbolt.io'

        Accepted optional kwargs
        ------------------------
        source : str
            default 'PYTHON' - allows to specify source so that this class
            can be called by other modules (CloudBolt, etc.). All OneFuse jobs will
            show this value as the Source of the job
        protocol : str
            default 'https' - Allows to specify non-standard protocol
        port : int
            default 443 - Allows to specify non-standard port
        verify_certs : bool
            default False - Allows to specify whether or not to verify
            OneFuse certs
        log_level : str
            default 'WARNING' - Allows more verbose logs to be shown. Valid options
            are: CRITICAL, ERROR, WARNING, INFO, DEBUG
        logger - allows you to pass in logger information. By default will log to
            onefuse.log as well as to console at the DEBUG level
        """
        try:
            source = kwargs["source"]
        except KeyError:
            source = "PYTHON"
        try:
            protocol = kwargs["protocol"]
        except KeyError:
            protocol = "https"
        try:
            port = kwargs["port"]
        except KeyError:
            port = 443
        try:
            verify_certs = kwargs["verify_certs"]
        except KeyError:
            verify_certs = False
        try:
            log_level = kwargs["log_level"]
        except:
            log_level = 'WARNING'
        try:
            logger = kwargs["logger"]
        except KeyError:
            # If no logger is passed in, assume being run from command line,
            # log to the console.
            numeric_level = getattr(logging, log_level.upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % log_level)
            # logging.basicConfig(filename='onefuse.log', level=numeric_level)
            logging.basicConfig(level=numeric_level)
            logger = logging.getLogger(__name__)
            # console_handler = logging.StreamHandler(sys.stdout)
            # logger.addHandler(console_handler)
        if not verify_certs:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            verify_certs = False
        self.username = username
        self.password = password
        self.verify_certs = verify_certs
        self.base_url = protocol + '://'
        self.base_url += host
        self.base_url += f':{port}'
        self.base_url += '/api/v3/onefuse'
        self.logger = logger
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Origin-Host': socket.gethostname(),
            'Connection': 'Keep-Alive',
            'SOURCE': source
        }
        self.onefuse_version = self.get_onefuse_version()

    def __enter__(self):
        return self

    def __getattr__(self, item):
        if item == 'get':
            return lambda path, **kwargs: requests.get(
                self.base_url + path,
                auth=HTTPBasicAuth(self.username, self.password),
                headers=self.headers,
                verify=self.verify_certs,
                **kwargs
            )
        elif item == 'post':
            return lambda path, **kwargs: requests.post(
                self.base_url + path,
                auth=HTTPBasicAuth(self.username, self.password),
                headers=self.headers,
                verify=self.verify_certs,
                **kwargs
            )
        elif item == 'delete':
            return lambda path, **kwargs: requests.delete(
                self.base_url + path,
                auth=HTTPBasicAuth(self.username, self.password),
                headers=self.headers,
                verify=self.verify_certs,
                **kwargs
            )
        elif item == 'put':
            return lambda path, **kwargs: requests.put(
                self.base_url + path,
                auth=HTTPBasicAuth(self.username, self.password),
                headers=self.headers,
                verify=self.verify_certs,
                **kwargs
            )
        else:
            return item

    def __repr__(self):
        return 'OneFuseManager'

    # AD Functions:
    def provision_ad(self, policy_name: str, template_properties: dict,
                     name: str, tracking_id: str = ""):
        """
        Provision an Active Directory Object

        Parameters
        ----------
        policy_name : str
            OneFuse Active Directory Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        name : str
            The name of the Active Directory Computer object to be created
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get AD Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'microsoftADPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request AD
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
            "name": name,
        }
        url = "/microsoftADComputerAccounts/"
        response_json = self.request(url, template, tracking_id)
        return response_json

    def deprovision_ad(self, ad_id: int):
        """
        De-Provision an Active Directory Object

        Parameters
        ----------
        ad_id : str
            OneFuse ID of the Active Directory object to be de-provisioned
        """
        path = f'/microsoftADComputerAccounts/{ad_id}/'
        self.deprovision_mo(path)
        return path

    def move_ou(self, ad_id: int):
        """
        Move an Active Directory object currently in the build state to the
        final OU/state

        Parameters
        ----------
        ad_id : int
            OneFuse ID of the Active Directory object to be moved
        """
        path = f'/microsoftADComputerAccounts/{ad_id}/'
        get_response = self.get(path)
        get_response.raise_for_status()
        get_response = get_response.json()
        state = get_response["state"]
        if state != 'build':
            msg = (f'Active Directory object is in {state} state this method '
                   f'only moves objects from "build" to "final"')
            raise OneFuseError(msg)

        final_ou = get_response["finalOu"]
        name = get_response["name"]
        links = get_response["_links"]
        workspace_url = links["workspace"]["href"]
        tracking_id = self.get_tracking_id_from_mo(path)
        template = {
            "workspace": workspace_url,
            "state": "final"
        }
        self.logger.info(f'Moving AD object: {name} to final OU: {final_ou}')
        response_json = self.request(path, template, tracking_id, "put")
        self.logger.info(f"AD object was successfully moved to the final OU. "
                         f"AD: {name}, OU: {final_ou}")
        return response_json

    # Ansible Tower Functions
    def provision_ansible_tower(self, policy_name: str,
                                template_properties: dict, hosts: str = '',
                                limit: str = '', tracking_id: str = ""):
        """
        Provision an Ansible Tower Deployment

        Parameters
        ----------
        policy_name : str
            OneFuse Ansible Tower Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        hosts : str - optional
            Comma separated string of Ansible Tower Hosts. This is taken as a
            string input because it is rendered, allowing for loops, and other
            jinja syntax to be leveraged
        limit : str - optional
            Ansible Tower Limit override
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Ansible Tower Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'ansibleTowerPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Render hosts and limit
        hosts_arr = []
        if hosts:
            rendered_hosts = self.render(hosts, template_properties)
            for host in rendered_hosts.split(','):
                hosts_arr.append(host.strip())
        if limit:
            rendered_limit = self.render(limit, template_properties)
        else:
            rendered_limit = ''
        # Request Ansible Tower
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "templateProperties": template_properties,
            "hosts": hosts_arr,
            "limit": rendered_limit
        }
        path = "/ansibleTowerDeployments/"
        response_json = self.request(path, template, tracking_id)
        if response_json and "provisioningJobResults" in response_json:
            job_results = response_json["provisioningJobResults"]
            if job_results:
                last_job_result = job_results[-1]
                playbook_name = last_job_result.get("jobTemplatePlaybookName", "Unknown Playbook")
                jobtemplate_name = last_job_result.get("jobTemplateName", "Unknown JobTemplate")
                self.logger.info(f"The last jobtemplate/playbook executed in Ansible through OneFuse: {playbook_name}/{jobtemplate_name}")
            else:
                self.logger.warning("No provisioning job results found in the response.")
        else:
            self.logger.error("Invalid response or missing 'provisioningJobResults'.")
        return response_json

    def deprovision_ansible_tower(self, at_id: int):
        """
        De-Provision an Ansible Tower Object

        Parameters
        ----------
        at_id : str
            OneFuse ID of the Ansible Tower Deployment object to be
            de-provisioned
        """
        path = f'/ansibleTowerDeployments/{at_id}/'
        self.deprovision_mo(path)
        return path

    # DNS Functions
    def provision_dns(self, policy_name: str, template_properties: dict,
                      name: str, value: str, zones: list,
                      tracking_id: str = ""):
        """
        Provision an DNS Reservation

        Parameters
        ----------
        policy_name : str
            OneFuse DNS Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        name : str
            Name for the DNS reservation, typically a hostname
        value : str
            Value for the reservation, typically an IP Address
        zones : list
            List of Zones to add the reservation to. eg:
                ["cloudbolt.io", "cloudboltsoftware.com"]
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get DNS Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'dnsPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        rendered_zones = []
        for zone in zones:
            rendered_zone = self.render(zone, template_properties)
            rendered_zones.append(rendered_zone)
        # Request DNS
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
            "name": name,
            "value": value,
            "zones": rendered_zones
        }
        path = "/dnsReservations/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_dns(self, dns_id: int):
        """
        De-Provision a DNS Reservation

        Parameters
        ----------
        dns_id : str
            OneFuse ID of the DNS Reservation to be de-provisioned
        """
        path = f'/dnsReservations/{dns_id}/'
        self.deprovision_mo(path)
        return path

    # IPAM Functions
    def provision_ipam(self, policy_name: str, template_properties: dict,
                       hostname: str, tracking_id: str = ""):
        """
        Provision an IPAM Reservation

        Parameters
        ----------
        policy_name : str
            OneFuse IPAM Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        hostname : str
            Hostname that the IPAM reservation is being made for. Will be set
            in the downstream IPAM provider
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get IPAM Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'ipamPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request IPAM
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
            "hostname": hostname
        }
        path = "/ipamReservations/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_ipam(self, ipam_id: int):
        """
        De-Provision an IPAM Reservation

        Parameters
        ----------
        ipam_id : str
            OneFuse ID of the IPAM Reservation to be de-provisioned
        """
        path = f'/ipamReservations/{ipam_id}/'
        self.deprovision_mo(path)
        return path

    # Pluggable Modules
    def export_pluggable_module(self, module_name: str, save_path: str,
                                overwrite: bool = False):
        """
        Export a Pluggable Module to a file path. The exported module will be
        saved to a file

        Parameters
        ----------
        module_name : str
            The name of the module to export
        save_path : str
            File path to save the exported module zip file to
            Windows: 'C:\\temp\\onefuse_backups\\'
            Linux: '/tmp/onefuse_backups/'
        overwrite : bool
            Boolean value whether to overwrite an existing file in save_path
            Defaults to False
        """
        path = 'modules'
        module = self.get_policy_by_name(path, module_name)
        module_id = module["id"]
        export_path = f'/{path}/{module_id}/export/'
        response = self.post(export_path, stream=True)
        response.raise_for_status()
        if not os.path.exists(os.path.dirname(save_path)):
            try:
                os.makedirs(os.path.dirname(save_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        file_path = f'{save_path}{module_name}.zip'
        if os.path.isfile(file_path):
            if overwrite:
                os.remove(file_path)
            else:
                raise OneFuseError(f'Zip file already exists for module_name: '
                                   f'{module_name} in save_path: {save_path}')
        with open(file_path, 'wb') as fd:
            for chunk in response.iter_content(chunk_size=128):
                fd.write(chunk)
        self.logger.info(f'Module: {module_name} has been saved to: '
                         f'{file_path}')
        return None

    def upload_pluggable_module(self, file_path: str,
                                replace_existing: bool = False):
        """
        Upload a Pluggable Module zip file from a file path.

        Parameters
        ----------
        file_path : str
            File path to the module zip file
            Windows: 'C:\\temp\\onefuse_backups\\modules\\f5.zip'
            Linux: '/tmp/onefuse_backups/modules/f5.zip'
        replace_existing : bool
            Boolean to replace the module if it already exists. If False is
            selected, this will create a new module with a similar name.
            Default - False

        """
        path = '/modules/'
        if os.name == 'nt':
            path_char = '\\'
        else:
            path_char = '/'
        file_object = open(file_path, 'rb')
        files = {'zipFile': ('upload.zip', file_object)}
        data = {'replaceExisting': json.dumps(replace_existing)}
        try:
            # Can't use the ofm.post method here, file uploads require
            # different headers than are provided by the class
            response = requests.post(
                self.base_url + path,
                auth=HTTPBasicAuth(self.username, self.password),
                verify=self.verify_certs,
                data=data,
                files=files
            )
            response.raise_for_status()
        except HTTPError as err:
            err_msg = (f'Request failed for path: {path}, Error: '
                       f'{sys.exc_info()[0]}. {sys.exc_info()[1]}'
                       f', line: {sys.exc_info()[2].tb_lineno}. Messages: ')
            errors = json.loads(err.response.content)["errors"]
            err_msg += ','.join(error["message"] for error in errors)
            raise OneFuseError(err_msg)
        return response

    def provision_module(self, policy_name: str, template_properties: dict,
                         tracking_id: str = ""):
        """
        Provision a managed object by executing a OneFuse Pluggable Module

        Parameters
        ----------
        policy_name : str
            OneFuse Pluggable Module Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get CMDB Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'modulePolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
        }
        path = '/moduleManagedObjects/'
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_module(self, mo_id: int):
        """
        De-Provision a Pluggable Module Managed Object

        Parameters
        ----------
        mo_id : str
            OneFuse ID of the IPAM Reservation to be de-provisioned
        """
        path = f'/moduleManagedObjects/{mo_id}/'
        self.deprovision_mo(path)
        return path

    # Naming Functions
    def provision_naming(self, policy_name: str, template_properties: dict,
                         tracking_id: str = ""):
        """
        Provision a Name

        Parameters
        ----------
        policy_name : str
            OneFuse Naming Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'namingPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Machine Custom Name
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
        }
        path = "/customNames/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_naming(self, name_id: int):
        """
        De-Provision a Name

        Parameters
        ----------
        name_id : str
            OneFuse ID of the Name to be de-provisioned
        """
        path = f'/customNames/{name_id}/'
        self.deprovision_mo(path)
        return path

    # Property Toolkit
    def get_sps_properties(self, template_properties: dict,
                           upstream_property: str = "",
                           ignore_properties: list = None):
        """
        Parse a dict to find any OneFuse property toolkit properties
        (OneFuse_SPS_<uniqueName>). Add all properties from all OneFuse_SPS
        properties found to the input dict and return the dict.

        Parameters
        ----------
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        upstream_property : str
            You can pass in a property corresponding to an upstream provider to
            pull all key:values contained in that key to the root level. eg:
            {
                "OneFuse_CB_Props": {
                    "prop1": "value1",
                    "prop2": "value2"
                }
            }
            If OneFuse_CB_Props is passed in as the upstream property, this
            method would return:
            {
                "prop1": "value1",
                "prop2": "value2"
            }
        ignore_properties : list
            A list of properties inside the property set to ignore. This allows
            certain properties to not be returned in the dict.
        """
        try:
            if ignore_properties is None:
                ignore_properties = []
            # Get Unsorted list of keys that match OneFuse_SPS_
            sps_keys = []
            pattern = re.compile(PROPERTY_SET_PREFIX)
            for key in template_properties.keys():
                result = pattern.match(key)
                if result is not None:
                    sps_keys.append(key)

            # Sort list alphanumerically.
            sps_keys.sort()

            # Gather Properties
            sps_properties = {}
            for key in sps_keys:
                self.logger.debug(
                    f'Starting get_sps_all_properties key: {key}')
                sps_name = template_properties[key]
                sps_json = self.get_sps_by_name(sps_name)
                props = sps_json["properties"]
                for prop_key in props.keys():
                    if prop_key == upstream_property:
                        upstream_value = props[prop_key]
                        for upstream_key in upstream_value.keys():
                            sps_properties[upstream_key] = upstream_value[
                                upstream_key]
                    else:
                        try:
                            ignore_properties.index(prop_key)
                            self.logger.debug(
                                f'An upstream ignore value '
                                f'was found, ignoring property. '
                                f'Ignore property: {prop_key}')
                        except:
                            sps_properties[prop_key] = props[prop_key]
        except Exception:
            raise OneFuseError(
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                f'line: {sys.exc_info()[2].tb_lineno}')

        return sps_properties

    def get_sps_by_name(self, sps_name: str):
        """
        Return a OneFuse Property set by the name

        Parameters
        ----------
        sps_name : dict
            Name of the Property Set to be returned
        """
        path = f'/propertySets/?filter=name.iexact:"{sps_name}"'
        response = self.get(path)
        response.raise_for_status()
        sps_json = response.json()

        if sps_json["count"] > 1:
            raise (f"More than one Property Set was returned "
                   f"matching the name: {sps_name}. Response: "
                   f"{json.dumps(sps_json)}")

        if sps_json["count"] == 0:
            raise OneFuseError(
                f"No property sets were returned matching the"
                f" name: {sps_name}. Response: "
                f"{json.dumps(sps_json)}")
        sps_json = sps_json["_embedded"]["propertySets"][0]
        return sps_json

    def get_create_properties(self, template_properties: dict):
        """
        Parse a dict to find any properties prepended with
        OneFuse_CreateProperties_. If found, extract the key:value out of the
        property and return them as a dict. Supports both single objects and arrays of objects.

        Ex:
        {
            "root_prop":"root_value"
            "OneFuse_CreateProperties_Test": {
                "key": "name_app1",
                "value": "apache"
            },
            "OneFuse_CreateProperties_Apps": [
                {"key": "name_app2", "value": "nginx"},
                {"key": "name_app3", "value": "mysql"}
            ]
        }
        The above JSON when passed in to this function would return:
        {
            "name_app1": "apache",
            "name_app2": "nginx",
            "name_app3": "mysql"
        }

        Parameters
        ----------
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        """
        create_properties = {}
        pattern = re.compile('OneFuse_CreateProperties_')
        for key in template_properties.keys():
            # Match the key against a defined pattern
            result = pattern.match(key)
            if result is not None:
                self.logger.debug(f'Starting parse of key: {key}, '
                                f'value: {template_properties[key]}')
                value_obj = template_properties[key]
                self.logger.debug(f'Create Props Object: {value_obj}')

                # If the value_obj is a string, parse JSON.
                if isinstance(value_obj, str):
                    value_obj = json.loads(value_obj)

                # If the value_obj is a list (array of key/value pairs).
                if isinstance(value_obj, list):
                    for item in value_obj:
                        # If the item is a dictionary containing both 'key' and 'value'
                        if isinstance(item, dict) and "key" in item and "value" in item:
                            # Add the 'key' and 'value' from the item to the create_properties dictionary
                            create_properties[item["key"]] = item["value"]
                # If the value_obj is a single key/value pair containing both 'key' and 'value'
                elif isinstance(value_obj, dict) and "key" in value_obj and "value" in value_obj:
                    # Add the 'key' and 'value' from the dictionary to the create_properties dictionary
                    create_properties[value_obj["key"]] = value_obj["value"]
        return create_properties

    # Scripting
    def provision_scripting(self, policy_name: str, template_properties: dict,
                            tracking_id: str = ""):
        """
        Provision a Scripting Deployment

        Parameters
        ----------
        policy_name : str
            OneFuse Scripting Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Scripting Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'scriptingPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
        }
        path = "/scriptingDeployments/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_scripting(self, script_id: int):
        """
        De-Provision an Scripting Deployment

        Parameters
        ----------
        script_id : str
            OneFuse ID of the Scripting Deployment to be de-provisioned
        """
        path = f'/scriptingDeployments/{script_id}/'
        self.deprovision_mo(path)
        return path

    # ServiceNow CMDB Functions
    def provision_cmdb(self, policy_name: str, template_properties: dict,
                       tracking_id: str = ""):
        """
        Provision a ServiceNow CMDB Deployment

        Parameters
        ----------
        policy_name : str
            OneFuse ServiceNow CMDB Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get CMDB Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        policy_path = 'servicenowCMDBPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
        }
        path = "/servicenowCMDBDeployments/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def update_cmdb(self, template_properties: dict, cmdb_id: int):
        """
        Update a ServiceNow CMDB Deployment

        Parameters
        ----------
        cmdb_id : str
            OneFuse ID of the ServiceNow CMDB deployment to be updated
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        """
        # Get Existing Object
        path = f'/servicenowCMDBDeployments/{cmdb_id}/'
        current_response = self.get(path)
        current_response.raise_for_status()
        current_json = current_response.json()
        tracking_id = self.get_tracking_id_from_mo(path)
        # Template
        template = {
            "policy": current_json["_links"]["policy"]["href"],
            "templateProperties": template_properties,
            "workspace": current_json["_links"]["workspace"]["href"],
        }
        # Send Put request
        response_json = self.request(path, template, tracking_id, 'put')
        return response_json

    def deprovision_cmdb(self, cmdb_id: int):
        """
        De-Provision a ServiceNow CMDB Deployment

        Parameters
        ----------
        cmdb_id : str
            OneFuse ID of the ServiceNow CMDB Deployment to be de-provisioned
        """
        path = f'/servicenowCMDBDeployments/{cmdb_id}/'
        self.deprovision_mo(path)
        return path

    # vRealize Automation Functions
    def provision_vra(self, policy_name: str, template_properties: dict,
                      deployment_name: str, tracking_id: str = ""):
        """
        Provision a OneFuse vRA Deployment

        Parameters
        ----------
        policy_name : str
            OneFuse vRA Policy Name
        template_properties : dict
            Stack of properties used in OneFuse policy execution
        deployment_name : str
            Name to set in vRA for the deployment being provisioned
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get CMDB Policy by Name
        rendered_policy_name = self.render(policy_name, template_properties)
        rendered_deployment_name = self.render(deployment_name,
                                               template_properties)
        policy_path = 'vraPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": template_properties,
            "workspace": workspace_url,
            "deploymentName": rendered_deployment_name
        }
        path = '/vraDeployments/'
        sleep_seconds = 30
        response_json = self.request(path, template, tracking_id,
                                     sleep_seconds=sleep_seconds)
        return response_json

    def deprovision_vra(self, vra_id: int):
        """
        De-Provision a vRA Deployment

        Parameters
        ----------
        vra_id : str
            OneFuse ID of the vRA Deployment to be de-provisioned
        """
        path = f'/vraDeployments/{vra_id}/'
        self.deprovision_mo(path)
        return path

    # Utilities common to all Python Platforms
    def render(self, template: str, template_properties: dict,
               return_type: str = "value"):
        """
        Leverage the OneFuse template tester to render any jinja2 syntax.

        Parameters
        ----------
        template : str
            The string to be rendered. Ex: "This is {{ owner }}'s deployment"
        template_properties : dict
            Stack of properties used in OneFuse policy execution
            Example for above:
            {
                "owner": "jdoe"
            }
            Result: "This is jdoe's deployment"
        return_type : str
            Optional. Valid Values: "value", "resolvedProperties". "value" will
            return the result of the rendered template, "resolvedProperties"
            will return the entire resolved properties stack (Dynamic Property
            Set). Default: "value"
        """
        try:
            if type(template) != str:
                return template
            if template.find('{%') == -1 and template.find('{{') == -1:
                return template
            json_template = {
                "template": template,
                "templateProperties": template_properties,
            }
            response = self.post("/templateTester/", json=json_template)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get(return_type)
        except:
            error_string = (
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                f'line: {sys.exc_info()[2].tb_lineno}. Template: '
                f'{template}')
            self.logger.error(error_string)
            raise

    def resolve_properties(self, template_properties: dict):
        """
        Leverage the OneFuse template tester to render an entire template
        properties stack. Returns rendered properties. Will find and expand any
        properties prepended with 1FPS_

        Parameters
        ----------
        template_properties : dict
            Stack of properties used in OneFuse policy execution
            Example:
            {
                "owner": "jdoe",
                "text": "This is {{owner}}'s machine",
                "1FPS_env": "dev"
            }
            Result:
            {
                "owner": "jdoe",
                "text": "This is jdoe's deployment",
                "nameEnv": "dev",                       # From 1FPS_env
                "ipamEnv": "Development",               # From 1FPS_env
                "dnsZone": "dev.cloudbolt.io"           # From 1FPS_env
            }
        """
        try:
            json_template = {
                "template": "",
                "templateProperties": template_properties,
            }
            response = self.post("/templateTester/", json=json_template)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get("resolvedProperties")
        except:
            error_string = (
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                f'line: {sys.exc_info()[2].tb_lineno}.')
            self.logger.error(error_string)
            raise

    def get_job_json(self, job_id: int):
        """
        Return the json payload for a OneFuse Job ID

        Parameters
        ----------
        job_id : str
            The Job ID to return the job payload for
        """
        job_path = f'/jobMetadata/{job_id}/'
        job_response = self.get(job_path)
        job_json = job_response.json()
        return job_json

    def wait_for_job_completion(self, job_response: requests.models.Response,
                                path: str, method: str,
                                sleep_seconds: int = 5):
        """
        Continuously poll a OneFuse job until completion. Raise a TimeoutError
        when the max timeout per module is exceeded. Returns the json for the
        OneFuse Managed Object that was created.

        Parameters
        ----------
        job_response : requests.models.Response
            The response from the requests module for a OneFuse Job request
        path : str
            The REST path for the policy executed. ex: '/customNames/'
        method : str
            The type of method called for the original job. ex: "put"
        sleep_seconds : int
            The interval of which to sleep polling the job for. Defaults to 5
        """
        response_json = job_response.json()
        response_status = job_response.status_code
        self.logger.debug(f'OneFuse Post Response status: {response_status}')
        # Async returns a 202
        if response_status == 202:
            import time
            job_id = response_json["id"]
            total_seconds = 0
            max_sleep = self.get_max_sleep(path)
            job_json = self.get_job_json(job_id)
            job_state = job_json["jobState"]
            while job_state != 'Successful' and job_state != 'Failed':
                self.logger.debug(
                    f'Waiting for job completion. Sleeping for {sleep_seconds}'
                    f' seconds. Job state: {job_state}')
                time.sleep(sleep_seconds)
                total_seconds += sleep_seconds
                if total_seconds > max_sleep:
                    raise TimeoutError(f'Action timeout. OneFuse job exceeded '
                                       f'{max_sleep} seconds')
                job_json = self.get_job_json(job_id)
                job_state = job_json["jobState"]
            if job_state == 'Successful':
                if method == 'delete':
                    return None
                self.logger.debug('OneFuse Job Successful')
                mo_string = job_json["responseInfo"]["payload"]
                mo_json = json.loads(mo_string)
                mo_json["trackingId"] = job_json["jobTrackingId"]
            else:
                payload = json.loads(job_json["responseInfo"]["payload"])
                error_string = f'OneFuse job failure. State: {job_state}, ' \
                               f'Error Code: {payload["code"]}, Errors: '
                errors = payload["errors"]
                error_string += ', '.join(err["message"] for err in errors)
                self.logger.error(
                    f'OneFuse job failure. Error: {error_string}')
                if error_string.find("Required Variable is missing") > -1:
                    raise RequiredParameterMissing(error_string)
                raise OneFuseError(error_string)
        # Non-Async (ex: SPS) Returns a 201
        else:
            if method == 'delete':
                return None
            mo_json = response_json
            mo_json["trackingId"] = job_response.headers["Tracking-Id"]

        return mo_json

    def request(self, path: str, template: dict, tracking_id: str = "",
                method: str = 'post', **kwargs):
        """
        Submit a POST/PUT request to OneFuse. Supports handling async responses
        Used for submitting requests for policy executions.

        Accepted kwargs
        ---------------
        sleep_seconds : int
            Overrides the default of 5 seconds when polling a job to determine
            completion

        Parameters
        ----------
        path : str
            The REST path for the policy executed. ex: '/customNames/'
        template : dict
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        method : str - optional
            The type of method called for the original job. ex: 'put'. Default
            is 'post'
        """
        self.add_tracking_id_to_headers(tracking_id)
        self.logger.debug(f'Submitting {method} request to path: {path} with '
                          f' template_properties: {template}')
        try:
            if method == 'post':
                response = self.post(path, json=template)
            elif method == 'put':
                response = self.put(path, json=template)
            else:
                raise OneFuseError(
                    f'This action only supports post and put calls. '
                    f'Requested method: {method}')
            response.raise_for_status()
            try:
                sleep_seconds = kwargs["sleep_seconds"]
            except KeyError:
                sleep_seconds = 5
            mo_json = self.wait_for_job_completion(response, path, method,
                                                   sleep_seconds)
        except HTTPError as err:
            err_msg = (f'Request failed for path: {path}, Error: '
                       f'{sys.exc_info()[0]}. {sys.exc_info()[1]}'
                       f', line: {sys.exc_info()[2].tb_lineno}. Messages: ')
            errors = json.loads(err.response.content)["errors"]
            err_msg += ','.join(error["message"] for error in errors)
            raise OneFuseError(err_msg)
        except:
            raise
        self.logger.debug(f'mo_json: {mo_json}')
        return mo_json

    def get_object_by_unique_field(self, resource_path: str, field_value: str,
                                   field: str):
        """
        Get any OneFuse object by a unique field value. This function will
        throw an exception if more than one object is returned. Ex: Get a
        vRA deployment by deploymentName:
        get_object_by_unique_field('/vraDeployments/', 'My Deployment', 'deploymentName')

        Parameters
        ----------
        resource_path : str
            OneFuse REST path to object type. Ex: '/vraDeployments/'
        field_value : str
            Value of field to return results for. Ex: 'My Deployment'
        field : str
            Field to key off of. Ex: 'deploymentName'
        """
        path = f'/{resource_path}/?filter={field}.iexact:"{field_value}"'
        policies_response = self.get(path)
        policies_response.raise_for_status()
        policies_json = policies_response.json()

        if policies_json["count"] > 1:
            raise OneFuseError(f"More than one policy was returned matching "
                               f"the name: {field_value}. Response: "
                               f"{json.dumps(policies_json)}")

        if policies_json["count"] == 0:
            raise OneFuseError(f"No policies were returned matching the "
                               f"name: {field_value}. Response: "
                               f"{json.dumps(policies_json)}")
        policy_json = policies_json["_embedded"][resource_path][0]
        return policy_json

    def get_policy_by_name(self, policy_path: str, policy_name: str):
        """
        Return a OneFuse Policy JSON by Name

        Parameters
        ----------
        policy_path : str
            OneFuse REST path to policy type. Ex: '/namingPolicies/'
        policy_name : str
            Name of the Policy to return. Ex: 'Production'
        """
        policy_json = self.get_object_by_unique_field(policy_path, policy_name,
                                                      "name")
        return policy_json

    def deprovision_mo(self, path: str):
        """
        De-provision a OneFuse Managed Object and wait for completion

        Parameters
        ----------
        path : str
            Complete path to the object to delete to include ID.
            Ex: '/api/v3/onefuse/customNames/782/'
        """
        tracking_id = self.get_tracking_id_from_mo(path)
        try:
            self.logger.info(f'Deleting object from url: {path}, tracking_id: '
                             f'{tracking_id}')
            self.add_tracking_id_to_headers(tracking_id)
            delete_response = self.delete(path)
            delete_response.raise_for_status()
            self.wait_for_job_completion(delete_response, path, 'delete')
            self.logger.info(f"Object deleted from the OneFuse database. "
                             f"Path: {path}")
        except:
            self.logger.error(f'Deprovision failed for path: {path} '
                              f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}'
                              f', line: {sys.exc_info()[2].tb_lineno}')
            raise

    def get_tracking_id_from_mo(self, path: str):
        """
        Get the OneFuse Tracking ID from a Managed Object

        Parameters
        ----------
        path : str
            Complete path to the object to the MO to include ID.
            Ex: '/api/v3/onefuse/customNames/782/'
        """
        try:
            self.logger.debug(f'Getting object from url: {path}')
            get_response = self.get(path)
            get_response.raise_for_status()
            get_json = get_response.json()
            full_job_path = get_json["_links"]["jobMetadata"]["href"]
            job_path = full_job_path.replace('/api/v3/onefuse', '')
            job_response = self.get(job_path)
            job_response.raise_for_status()
            job_json = job_response.json()
            tracking_id = job_json["jobTrackingId"]
        except:
            self.logger.info('Tracking ID could not be determined for MO. '
                             'OneFuse will create a Tracking ID')
            tracking_id = ""
        return tracking_id

    def get_max_sleep(self, path: str):
        """
        Determine the maximum sleep time for a module

        Parameters
        ----------
        path : str
           OneFuse REST path to policy type. Ex: '/namingPolicies/'
        """
        try:
            if path == '/customNames/':
                max_sleep = 10
            elif path == '/ipamReservations/':
                max_sleep = 10
            elif path == '/dnsReservations/':
                max_sleep = 10
            elif path == '/microsoftADComputerAccounts/':
                max_sleep = 15
            elif path == '/scriptingDeployments/':
                max_sleep = 90
            elif path == '/ansibleTowerDeployments/':
                max_sleep = 120
            elif path == '/vraDeployments/':
                max_sleep = 120
            else:
                max_sleep = 10
        except:
            max_sleep = 10
        max_sleep_seconds = max_sleep * 60
        self.logger.debug(f'max_sleep_seconds: {max_sleep_seconds}')
        return max_sleep_seconds

    def add_tracking_id_to_headers(self, tracking_id: str = ""):
        """
        Insert the OneFuse Tracking ID in to the headers for a request

        Parameters
        ----------
        tracking_id : str - optional
            OneFuse Tracking ID.
        """
        if tracking_id is not None and tracking_id != "":
            self.headers["Tracking-Id"] = tracking_id

    def create_tracking_id(self):
        """
        Generate a UUID to be used as a OneFuse Tracking ID. This is useful
        when Tracking ID may be needed prior to submitting a request.
        """
        tracking_id = uuid1().__str__()
        self.logger.debug(f'Tracking id created: {tracking_id}')
        return tracking_id

    def get_onefuse_version(self):
        """
        Get the version of the current instantiated OneFuse Appliance
        """
        response = self.get('/productInfo')
        response.raise_for_status()
        response_json = response.json()
        version = response_json["version"]
        return version

    def get_onefuse_instance_id(self):
        response = self.get('/productInfo')
        response.raise_for_status()
        response_json = response.json()
        try:
            instance_id = response_json["instanceId"]
            return instance_id
        except KeyError:
            self.logger.info(f'Unable to return Instance ID, version is < '
                             f'1.4')
            return None

    def ingest_name(self, policy_name: str, name: str,
                    dns_suffix: str = "", template_properties: dict = None,
                    tracking_id: str = ""):
        """
        Ingest an existing name to OneFuse - the policy will not execute but
        an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse Custom Naming Policy Name
        name : str
            Name for the Name object, typically a hostname
        dns_suffix : str
            Value for the DNS Suffix. Ex: 'example.com'
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'namingPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Ingest Name
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "name": name,
            "dnsSuffix": dns_suffix,
            "templateProperties": template_properties
        }
        path = "/customNames/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def ingest_dns_reservation(self, policy_name: str, name: str,
                               records: List[dict],
                               template_properties: dict = None,
                               tracking_id: str = ""):
        """
        Ingest an existing DNS Reservation to OneFuse - the policy will not
        execute but an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse DNS Policy Name
        name : str
            Name for the Name object, typically a hostname
        records : list(dict
            List of records to be included in DNS reservation.
            Ex: [{"type": "a", "value": "10.1.0.60", "name": "test.example.com"}]
            Valid types: a, ptr, host (infoblox only)
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'dnsPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Validate records
        for record in records:
            if record["type"] not in ["a", "ptr", "host"]:
                raise ValueError(f"Invalid DNS record type: {record['type']}")
        # Ingest DNS Reservation
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "name": name,
            "records": records,
            "templateProperties": template_properties
        }
        path = "/dnsReservations/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def ingest_ip_address(self, policy_name: str, ip_address: str,
                          hostname: str, subnet: str, primary_dns: str = None,
                          secondary_dns: str = None, dns_suffix: str = None,
                          dns_search_suffixes: str = None, gateway: str = None,
                          netmask: str = None, network: str = None,
                          template_properties: dict = None,
                          nic_label: str = None, tracking_id: str = ""):
        """
        Ingest an existing IP Address to OneFuse - the policy will not
        execute but an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse IPAM Policy Name
        ip_address : str
            IP Address for the IP Address object. Ex: '10.1.0.25
        hostname : str
            Hostname for the IP Address object. Ex. 'myhost.example.com'
        subnet : str
            Value for the Subnet in CIDR notation. Ex: '10.1.0.0/24'
        primary_dns : str
            Optional Primary DNS for the IP Address object. Ex: '10.0.0.10
        secondary_dns : str
            Optional Secondary DNS for the IP Address object. Ex: '10.0.0.10
        dns_suffix : str
            Optional Value for the DNS Suffix. Ex: 'example.com'
        dns_search_suffixes : str
            Optional Value for the DNS Search Suffixes. Comma separated.
            Ex: 'example.com,example2.com'
        gateway : str
            Optional Value for the Gateway. Ex: '10.1.0.1'
        netmask : str
            Optional Value for the Netmask. Ex: '255.255.255.0'
        network : str
            Optional Value for the Network. Ex: 'NameOfPortGroupInVcenter'
        nic_label : str
            Optional - Value for the NIC Label. Ex: 'eth0'
        template_properties : dict
            Optional - Dictionary of template properties. Ex: {'key': 'value'}
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'ipamPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Ingest IP Address
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "ipAddress": ip_address,
            "hostname": hostname,
            "primaryDns": primary_dns,
            "secondaryDns": secondary_dns,
            "dnsSuffix": dns_suffix,
            "dnsSearchSuffixes": dns_search_suffixes,
            "nicLabel": nic_label,
            "gateway": gateway,
            "netmask": netmask,
            "network": network,
            "subnet": subnet,
            "templateProperties": template_properties
        }
        path = "/ipamReservations/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def ingest_scripting_deployment(self, policy_name: str,
                                    provisioning_details: dict,
                                    deprovisioning_details: dict,
                                    template_properties: dict = None,
                                    tracking_id: str = ""):
        """
        Ingest an existing Scripting Deployment to OneFuse - the policy will not
        execute but an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse Scripting Policy Name
        provisioning_details : dict
           Scripting provisioning details.
           Ex. {"status": "successful", "output": []}
        deprovisioning_details : dict
            Scripting deprovisioning details
        template_properties : dict
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'scriptingPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Ingest Scripting Deployment
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "provisioning_details": provisioning_details,
            "deprovisioning_details": deprovisioning_details,
            "templateProperties": template_properties
        }
        path = "/scriptingDeployments/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def ingest_ad(self, policy_name: str, name: str, final_ou: str,
                  build_ou: str, state: str = "final",
                  security_groups: list = [], template_properties: dict = None,
                  tracking_id: str = ""):
        """
        Ingest an existing AD object to OneFuse - the policy will not execute
        but an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse AD Policy Name
        name : str
            AD Name
        final_ou : str
            AD Final OU
        build_ou : str
            AD Build OU
        state : str - optional
            AD State. Default is 'final'
        security_groups : list - optional
            List of security groups to add to the AD.
        template_properties : dict - optional
            Dictionary of template properties. Ex: {'key': 'value'}
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'microsoftADPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Ingest AD
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "name": name,
            "finalOu": final_ou,
            "buildOu": build_ou,
            "state": state,
            "securityGroups": security_groups,
            "templateProperties": template_properties
        }
        path = "/microsoftADComputerAccounts/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def ingest_ansible_tower(self, policy_name: str, hosts: list, limit: str,
                             inventory_name: str,
                             template_properties: dict = None,
                             tracking_id: str = ""):
        """
        Ingest an existing Ansible Tower object to OneFuse - the policy will not
        execute but an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse Ansible Tower Policy Name
        hosts : list
            List of Ansible Tower hosts
        limit : str
            Ansible Tower limit
        inventory_name : str
            Ansible Tower inventory name
        template_properties : dict - optional
            Dictionary of template properties. Ex: {'key': 'value'}
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'ansibleTowerPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Ingest Ansible Tower
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "hosts": hosts,
            "limit": limit,
            "inventoryName": inventory_name,
            "templateProperties": template_properties
        }
        path = "/ansibleTowerDeployments/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def ingest_service_now_cmdb(self, policy_name: str,
                                configuration_items_info: list,
                                execution_details: dict,
                                template_properties: dict = None,
                                tracking_id: str = ""):
        """
        Ingest an existing Service Now CMDB object to OneFuse - the policy will not
        execute but an object will be added to the OneFuse database.

        Parameters
        ----------
        policy_name : str
            OneFuse Service Now CMDB Policy Name
        configuration_items_info : list
            List representing the configuration items to ingest.
            Ex: [{"ciClassName": "cmdb_ci_vmware_instance", "ciName": "ppportlapp019" }]
        execution_details : dict
            Dictionary of execution details.
        template_properties : dict - optional
            Dictionary of template properties. Ex: {'key': 'value'}
        tracking_id : str - optional
            OneFuse Tracking ID. If not passed, one will be returned from the
            execution. Tracking IDs allow for grouping all executions for a
            single object
        """
        # Get Naming Policy by Name
        policy_path = 'servicenowCMDBPolicies'
        policy_json = self.get_policy_by_name(policy_path, policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Ingest Service Now CMDB
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "configurationItemsInfo": configuration_items_info,
            "executionDetails": execution_details,
            "templateProperties": template_properties
        }
        path = "/servicenowCMDBDeployments/ingest/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def delete_ingested_object(self, id: str, ingest_type: str):
        """
        Delete an ingested object from OneFuse - The deleted object will be
        removed from the OneFuse database without deprovisioning.

        Parameters
        ----------
        id : str
            ID for the object
        ingest_type : str
            Type of object to delete. Valid values: 'microsoftADComputerAccounts',
            'scriptingDeployments', 'ansibleTowerDeployments', 'customNames',
            'ansibleTowerPolicy', 'dnsReservations', 'ipamReservations',
            'servicenowCMDBDeployments', 'servicenowConnectorDeployments'
        """
        path = f"/{ingest_type}/{id}/ingest/"
        response_json = self.deprovision_mo(path)
        return response_json


if __name__ == '__main__':
    username = sys.argv[1]  # 'OneFuse Username'
    password = sys.argv[2]  # 'OneFuse Password'
    host = sys.argv[3]  # 'cloudbolt.example.com'
    path = sys.argv[4]  # '/namingPolicies/'
    with OneFuseManager(username, password, host) as onefuse:
        response = onefuse.get(path)

    print(json.dumps(response.json(), indent=True))
