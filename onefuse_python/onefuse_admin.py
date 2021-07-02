import re
import sys
import json
import requests
import socket
import logging
from requests.auth import HTTPBasicAuth
from .configuration.globals import STATIC_PROPERTY_SET_PREFIX, ROOT_PATH, \
    LOG_LEVEL

sys.path.append(ROOT_PATH)


# noinspection DuplicatedCode,PyBroadException,PyShadowingNames
class OneFuseManager(object):
    """
    This is a context manager class available to Python that facilitates
    easy API connectivity from a Python script host to a OneFuse host.

    Example 1 - Make custom REST calls to OneFuse:

        from onefuse_python.onefuse_admin import OneFuseManager
        ofm = OneFuseManager(username, password, host)
        response = ofm.get("/namingPolicies/")

    Example 2 - Provision Naming with OOB methods:
        from onefuse_python.onefuse_admin import OneFuseManager
        ofm = OneFuseManager(username, password, host)
        naming_json = ofm.provision_naming(self, policy_name, properties_stack,
                                           tracking_id)

    Accepted optional kwargs:
    - source - default 'PYTHON' - allows to specify source so that this class
        can be called by other modules (CloudBolt, etc.). All OneFuse jobs will
        show this value as the Source of the job
    - protocol - default 'https' - Allows to specify non-standard protocol
    - port - default 443 - Allows to specify non-standard port
    - verify_certs - default False - Allows to specify whether or not to verify
        OneFuse certs
    - logger - allows you to pass in logger information. By default will log to
        onefuse.log as well as to console at the LOG_LEVEL set in
        configuration.globals

    Authentication, headers, and url creation is handled within this class,
    freeing the caller from having to deal with these tasks.

    """

    def __init__(self,
                 username: str,
                 password: str,
                 host: str,
                 **kwargs):
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
            logger = kwargs["logger"]
        except KeyError:
            # If no logger is passed in, assume being run from command line,
            # log to onefuse.log as well as the console. Use the log level
            # set in configuration.globals
            numeric_level = getattr(logging, LOG_LEVEL.upper(), None)
            if not isinstance(numeric_level, int):
                raise ValueError('Invalid log level: %s' % LOG_LEVEL)
            logging.basicConfig(filename='onefuse.log', level=numeric_level)
            logger = logging.getLogger(__name__)
            console_handler = logging.StreamHandler(sys.stdout)
            logger.addHandler(console_handler)
        if not verify_certs:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            verify_certs = False
        self.conn_info = host
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
    def provision_ad(self, policy_name: str, properties_stack: dict,
                     tracking_id: str = ""):
        # Get AD Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'microsoftADPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request AD
        name = properties_stack["hostname"]
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
            "name": name,
        }
        url = "/microsoftADComputerAccounts/"
        response_json = self.request(url, template, tracking_id)
        return response_json

    def deprovision_ad(self, ad_id: int):
        path = f'/microsoftADComputerAccounts/{ad_id}/'
        self.deprovision_mo(path)
        return path

    def move_ou(self, ad_id: int):
        path = f'/microsoftADComputerAccounts/{ad_id}/'
        get_response = self.get(path)
        get_response.raise_for_status()
        get_response = get_response.json()
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
    def provision_ansible_tower(self, policy_name: str, properties_stack: dict,
                                hosts: str, limit: str, tracking_id: str = ""):
        # Get Ansible Tower Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'ansibleTowerPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Render hosts and limit
        hosts_arr = []
        if hosts:
            rendered_hosts = self.render(hosts, properties_stack)
            for host in rendered_hosts.split(','):
                hosts_arr.append(host.strip())
        if limit:
            rendered_limit = self.render(limit, properties_stack)
        else:
            rendered_limit = ''
        # Request Ansible Tower
        template = {
            "policy": policy_url,
            "workspace": workspace_url,
            "templateProperties": properties_stack,
            "hosts": hosts_arr,
            "limit": rendered_limit
        }
        path = "/ansibleTowerDeployments/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_ansible_tower(self, at_id: int):
        path = f'/ansibleTowerDeployments/{at_id}/'
        self.deprovision_mo(path)
        return path

    # DNS Functions
    def provision_dns(self, policy_name: str, properties_stack: dict,
                      ip_address: str, zones: list, tracking_id: str = ""):
        # Get DNS Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'dnsPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        rendered_zones = []
        for zone in zones:
            rendered_zone = self.render(zone, properties_stack)
            rendered_zones.append(rendered_zone)
        # Request DNS
        hostname = properties_stack["hostname"]
        value = ip_address
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
            "name": hostname,
            "value": value,
            "zones": rendered_zones
        }
        path = "/dnsReservations/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_dns(self, dns_id: int):
        path = f'/dnsReservations/{dns_id}/'
        self.deprovision_mo(path)
        return path

    # IPAM Functions
    def provision_ipam(self, policy_name: str, properties_stack: dict,
                       tracking_id: str = ""):
        # Get IPAM Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'ipamPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request IPAM
        hostname = properties_stack["hostname"]
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
            "hostname": hostname
        }
        path = "/ipamReservations/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_ipam(self, ipam_id: int):
        path = f'/ipamReservations/{ipam_id}/'
        self.deprovision_mo(path)
        return path

    # Naming Functions
    def provision_naming(self, policy_name: str, properties_stack: dict,
                         tracking_id: str = ""):
        # Get Naming Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'namingPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Machine Custom Name
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
        }
        path = "/customNames/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_naming(self, name_id: int):
        path = f'/customNames/{name_id}/'
        self.deprovision_mo(path)
        return path

    # Property Toolkit
    def get_sps_properties(self, properties_stack: dict,
                           upstream_property: str = "",
                           ignore_properties: list = []):
        try:
            # Get Unsorted list of keys that match OneFuse_SPS_
            sps_keys = []
            pattern = re.compile(STATIC_PROPERTY_SET_PREFIX)
            for key in properties_stack.keys():
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
                sps_name = properties_stack[key]
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
            raise Exception(
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                f'line: {sys.exc_info()[2].tb_lineno}')

        return sps_properties

    def get_sps_by_name(self, sps_name: str):
        path = f'/propertySets/?filter=name.iexact:"{sps_name}"'
        response = self.get(path)
        response.raise_for_status()
        sps_json = response.json()

        if sps_json["count"] > 1:
            raise Exception(f"More than one Static Property Set was returned "
                            f"matching the name: {sps_name}. Response: "
                            f"{json.dumps(sps_json)}")

        if sps_json["count"] == 0:
            raise Exception(
                f"No static property sets were returned matching the"
                f" name: {sps_name}. Response: "
                f"{json.dumps(sps_json)}")
        sps_json = sps_json["_embedded"]["propertySets"][0]
        return sps_json

    def get_create_properties(self, properties_stack: dict):
        create_properties = {}
        pattern = re.compile("OneFuse_CreateProperties_")
        for key in properties_stack.keys():
            result = pattern.match(key)
            if result is not None:
                self.logger.debug(f'Starting JSON parse of key: {key}, '
                                  f'value: {properties_stack[key]}')
                value_obj = properties_stack[key]
                self.logger.debug(f'Create Props Object: {value_obj}')
                if type(value_obj) == str:
                    value_obj = json.loads(value_obj)
                if value_obj["key"] and value_obj["value"]:
                    create_properties[value_obj["key"]] = value_obj["value"]
        return create_properties

    # Scripting
    def provision_scripting(self, policy_name: str, properties_stack: dict,
                            tracking_id: str = ""):
        # Get Scripting Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'scriptingPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
        }
        path = "/scriptingDeployments/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def deprovision_scripting(self, script_id: int):
        path = f'/scriptingDeployments/{script_id}/'
        self.deprovision_mo(path)
        return path

    # ServiceNow CMDB Functions
    def provision_cmdb(self, policy_name: str, properties_stack: dict,
                       tracking_id: str = ""):
        # Get CMDB Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        policy_path = 'servicenowCMDBPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
        }
        path = "/servicenowCMDBDeployments/"
        response_json = self.request(path, template, tracking_id)
        return response_json

    def update_cmdb(self, properties_stack: dict, cmdb_id: int):
        # Get Existing Object
        path = f'/servicenowCMDBDeployments/{cmdb_id}/'
        current_response = self.get(path)
        current_response.raise_for_status()
        current_json = current_response.json()
        tracking_id = self.get_tracking_id_from_mo(path)
        # Template
        template = {
            "policy": current_json["_links"]["policy"]["href"],
            "templateProperties": properties_stack,
            "workspace": current_json["_links"]["workspace"]["href"],
        }
        # Send Put request
        response_json = self.request(path, template, tracking_id, 'put')
        return response_json

    def deprovision_cmdb(self, cmdb_id: int):
        path = f'/servicenowCMDBDeployments/{cmdb_id}/'
        self.deprovision_mo(path)
        return path

    # vRealize Automation Functions
    def deprovision_vra(self, vra_id: int):
        path = f'/vraDeployments/{vra_id}/'
        self.deprovision_mo(path)
        return path

    # ServiceNow CMDB Functions
    def provision_vra(self, policy_name: str, properties_stack: dict,
                      deployment_name: str, tracking_id: str = ""):
        # Get CMDB Policy by Name
        rendered_policy_name = self.render(policy_name, properties_stack)
        rendered_deployment_name = self.render(deployment_name,
                                               properties_stack)
        policy_path = 'vraPolicies'
        policy_json = self.get_policy_by_name(policy_path,
                                              rendered_policy_name)
        links = policy_json["_links"]
        policy_url = links["self"]["href"]
        workspace_url = links["workspace"]["href"]
        # Request Scripting
        template = {
            "policy": policy_url,
            "templateProperties": properties_stack,
            "workspace": workspace_url,
            "deploymentName": rendered_deployment_name
        }
        path = '/vraDeployments/'
        sleep_seconds = 30
        response_json = self.request(path, template, tracking_id,
                                     sleep_seconds=sleep_seconds)
        return response_json

    # Utilities common to all Python Platforms
    def render(self, template: str, properties_stack: dict):
        try:
            if template.find('{%') == -1 and template.find('{{') == -1:
                return template
            template = {
                "template": template,
                "templateProperties": properties_stack,
            }
            response = self.post("/templateTester/", json=template)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get("value")
        except:
            error_string = (
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                f'line: {sys.exc_info()[2].tb_lineno}. Template: '
                f'{template}')
            self.logger.error(error_string)
            raise Exception(f'OneFuse Template Render failed. {error_string}')

    def get_job_json(self, job_id: int):
        job_path = f'/jobMetadata/{job_id}/'
        job_response = self.get(job_path)
        job_json = job_response.json()
        return job_json

    def wait_for_job_completion(self, job_response, path: str, method: str,
                                sleep_seconds: int = 5):
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
                    raise Exception(f'Action timeout. OneFuse job exceeded '
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
                error_msg = job_json["responseInfo"]["payload"]
                error_string = f'OneFuse job failure. {job_state}: {error_msg}'
                self.logger.error(
                    f'OneFuse job failure. Error: {error_string}')
                raise Exception(error_string)
        # Non-Async (ex: SPS) Returns a 201
        else:
            if method == 'delete':
                return None
            mo_json = response_json
            mo_json["trackingId"] = job_response.headers["Tracking-Id"]

        return mo_json

    def request(self, path: str, template: dict, tracking_id: str = "",
                method: str = 'post', **kwargs):
        # Addresses POST/PUT requests to OneFuse with async responses -
        # should be any policy executions. Creating a new SPS for example
        # doesn't use async
        # Submit request
        self.add_tracking_id_to_headers(tracking_id)
        self.logger.debug(f'Submitting {method} request to path: {path} with '
                          f' properties_stack: {template}')
        try:
            if method == 'post':
                response = self.post(path, json=template)
            elif method == 'put':
                response = self.put(path, json=template)
            else:
                raise Exception(
                    f'This action only supports post and put calls. '
                    f'Requested method: {method}')
            response.raise_for_status()
            try:
                sleep_seconds = kwargs["sleep_seconds"]
            except KeyError:
                sleep_seconds = 5
            mo_json = self.wait_for_job_completion(response, path, method,
                                                   sleep_seconds)
        except:
            error_string = (
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}, '
                f'line: {sys.exc_info()[2].tb_lineno}')
            self.logger.error(error_string)
            raise Exception(f'OneFuse Async call failed. {error_string}')
        self.logger.debug(f'mo_json: {mo_json}')
        return mo_json


    def get_object_by_unique_field(self, policy_path: str, policy_name: str,
                           field: str):
        path = f'/{policy_path}/?filter={field}.iexact:"{policy_name}"'
        policies_response = self.get(path)
        policies_response.raise_for_status()
        policies_json = policies_response.json()

        if policies_json["count"] > 1:
            raise Exception(f"More than one policy was returned matching "
                            f"the name: {policy_name}. Response: "
                            f"{json.dumps(policies_json)}")

        if policies_json["count"] == 0:
            raise Exception(f"No policies were returned matching the "
                            f"name: {policy_name}. Response: "
                            f"{json.dumps(policies_json)}")
        policy_json = policies_json["_embedded"][policy_path][0]
        return policy_json


    def get_policy_by_name(self, policy_path: str, policy_name: str):
        policy_json = self.get_object_by_unique_field(policy_path, policy_name,
                                                      "name")
        return policy_json


    def deprovision_mo(self, path: str):
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
            self.logger.error(
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}'
                f', line: {sys.exc_info()[2].tb_lineno}')

    def get_tracking_id_from_mo(self, path: str):
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
            self.logger.error(
                f'Error: {sys.exc_info()[0]}. {sys.exc_info()[1]}'
                f', line: {sys.exc_info()[2].tb_lineno}')
            self.logger.error('Tracking ID could not be determined for MO.')
            tracking_id = ""
        return tracking_id

    def get_max_sleep(self, path: str):
        try:
            if path == '/customNames/':
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_NAMING
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_NAMING
            elif path == '/ipamReservations/':
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_IPAM
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_IPAM
            elif path == '/dnsReservations/':
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_DNS
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_DNS
            elif path == '/microsoftADComputerAccounts/':
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_AD
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_AD
            elif path == '/scriptingDeployments/':
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_SCRIPTING
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_SCRIPTING
            elif path == '/ansibleTowerDeployments/':
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_ANSIBLETOWER
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_ANSIBLETOWER
            elif path == '/vraDeployments/':
                from .configuration.globals import ONEFUSE_ASYNC_TIMEOUT_VRA
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_VRA
            else:
                from .configuration.globals import \
                    ONEFUSE_ASYNC_TIMEOUT_OTHER
                max_sleep = ONEFUSE_ASYNC_TIMEOUT_OTHER
        except:
            from .configuration.globals import \
                ONEFUSE_ASYNC_TIMEOUT_OTHER
            max_sleep = ONEFUSE_ASYNC_TIMEOUT_OTHER
        max_sleep_seconds = max_sleep * 60
        self.logger.debug(f'max_sleep_seconds: {max_sleep_seconds}')
        return max_sleep_seconds

    def add_tracking_id_to_headers(self, tracking_id: str = ""):
        if tracking_id is not None and tracking_id != "":
            self.headers["Tracking-Id"] = tracking_id


if __name__ == '__main__':
    username = sys.argv[1]  # 'OneFuse Username'
    password = sys.argv[2]  # 'OneFuse Password'
    host = sys.argv[3]  # 'cloudbolt.example.com'
    path = sys.argv[4]  # '/namingPolicies/'
    with OneFuseManager(username, password, host) as onefuse:
        response = onefuse.get(path)

    print(json.dumps(response.json(), indent=True))