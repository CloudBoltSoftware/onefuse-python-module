Onefuse Python Module
=====================
This is a context manager class available to Python that facilitates
easy API connectivity from a Python script host to a OneFuse host.

Installation
------------
You will want to install the latest version that matches the version of your
OneFuse appliance. To find available versions the following command will
cause pip to throw an error showing available versions: ::

    $pip install onefuse==versions

To install the OneFuse Python Module by version: ::

    $pip install onefuse==1.3.0

To install the Latest OneFuse Python Module: ::

    $ pip install onefuse

To upgrade OneFuse to the latest version if OneFuse is already installed: ::

    $ pip install onefuse --upgrade

Usage
-----

Import and instantiate a OneFuseManager::

    from onefuse.admin import OneFuseManager
    ofm = OneFuseManager(username, password, host)



Accepted optional kwargs
-------------------------
- source - default 'PYTHON' - allows to specify source so that this class can be called by other modules (CloudBolt, etc.). All OneFuse jobs will show this value as the Source of the job
- protocol - default 'https' - Allows to specify non-standard protocol
- port - default 443 - Allows to specify non-standard port
- verify_certs - default False - Allows to specify whether or not to verify OneFuse certs
- logger - allows you to pass in logger information. By default will log to onefuse.log as well as to console at the LOG_LEVEL set in configuration.globals

Authentication, headers, and url creation is handled within this class,
freeing the caller from having to deal with these tasks.


Examples
--------

Example 1 - Make custom REST calls to OneFuse::

    from onefuse.admin import OneFuseManager
    ofm = OneFuseManager(username, password, host)
    response = ofm.get('/namingPolicies/')

Example 2 - Provision Naming with OOB methods::
    
    from onefuse.admin import OneFuseManager
    ofm = OneFuseManager(username, password, host)
    naming_json = ofm.provision_naming(self, policy_name, properties_stack,
                                       tracking_id)
 
