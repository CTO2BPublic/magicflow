from dynaconf import Dynaconf
import yaml
import gitlab, base64

from magicflow.messaging import CommandMessage
from magicflow.libs.yaml_dumper import CustomDumper
from magicflow.libs.gitlab_service import GitlabDriver
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger(__name__)


def project_selector(stage, cloud_provider):
    project_id = f'{cloud_provider}/{stage}'
    logger.info(project_id)

    selector = {
        "gcp/dev": "123345678",
        "gcp/staging": "123345679",
        "gcp/sand": "123345670",
        "gcp/prod": "123345671"
    }
    found = selector.get(project_id, 2)
    if found != 2:
        return found
    else:
        raise Exception("Job not found")


def create_mr_nonprod(self, cmd: CommandMessage):
    """
        data-platform-multicloud update values.tfvars for new capability/instance

        Returns:
            Function returns Gitlab Merge request URL.
        """

    # retrieve all input arguments
    input_data = cmd.get_data()["input"]
    job_id = cmd.get_data()['job_id']
    stage = input_data['stage']
    jira_ticket = input_data['jira_ticket']
    environment = input_data['environment']
    cloud_provider = input_data['cloud_provider']
    capability = input_data['namespace']
    data_service_name = input_data['service']
    instance_name = input_data['instance']
    wflow_id = cmd.get_data()['workflow_id']
    title = f'MagicFlow workflow {wflow_id}'
    desc = f'https://api.sview.tenant.manage.cto2b.eu/#!/workflows/{wflow_id}'
    dir_path = environment + '/' + stage + '/' + "data-platform-multicloud"
    file_path = dir_path + "/values.tfvars"
    logger.info("Modification will be done to nonprod repository %s" %
                file_path)

    project_id = project_selector(stage, cloud_provider)
    gl = GitlabDriver(self.gitlab_api_token, project_id)

    # get project files
    try:
        f = gl.get_project_file(file_path)
    except gitlab.exceptions.GitlabGetError:
        logger.error("File %s not found in project %s" %
                     (project_id, file_path))
        return False

    # modify file content if needed
    file_content = base64.b64decode(f.content).decode("utf-8").strip('\n')
    file_content_m = file_content.replace(' ', '').replace('"', '')
    matches = [
        'instance_name=' + instance_name, 'capability=' + capability,
        'engine=' + data_service_name
    ]
    if all(x in file_content_m for x in matches):
        logger.info(
            "instance %s aleady exists in values.tfvars for %s, no MR needed" %
            (data_service_name, instance_name))
        return {
            "parameters": {
                "project_id": project_id,
                "mr_id": "0",
                "mr_created": "False"
            },
            "result": "No changes needed"
        }
    else:
        logger.info(
            "instance %s does not exist in values.tfvars for %s, MR needed" %
            (data_service_name, instance_name))
        updated_values = """
  {
    instance_name           = "%s",
    capability              = "%s",
    hosted_zone             = "%s.cto2b.eu",
    engine                  = "%s",
    user_management_enabled = true,
    static_auth_enabled     = false
  },
""" % (instance_name, capability, cloud_provider, data_service_name)
        values_tfvars = ''.join(
            list(file_content)[:-1] + list(updated_values) +
            list(file_content[-1]) + list('\n'))
        f.content = values_tfvars

        # push to gitlab
        mr = gl.push_mr(f,
                        branch=job_id,
                        title=title,
                        description=desc,
                        jira_ticket=jira_ticket)
        if mr:
            mr_id = mr["mr_id"]
            mr_url = mr["mr_url"]
            return {
                "output": mr,
                "parameters": {
                    "mr_created": "True",
                    "mr_id": mr_id,
                    "mr_url": mr_url,
                    "project_id": project_id
                },
                "result": f'MR [#{mr_id}]({mr_url}) created'
            }
        else:
            return mr.update({
                "parameters": {
                    "mr_created": "False",
                    "mr_id": "0",
                    "project_id": project_id
                }
            })


def create_mr_infraconfig(self, cmd: CommandMessage):
    """
        Updates infra-config values.yaml file by adding namespace to watchednamespaces.

        Returns:
            Function returns Gitlab Merge request URL.
        """

    # retrieve all input arguments
    input_data = cmd.get_data()["input"]
    job_id = cmd.get_data()['job_id']
    stage = input_data['stage']
    jira_ticket = input_data['jira_ticket']
    cloud_provider = input_data['cloud_provider']
    environment = input_data['environment']
    ns = input_data['namespace']
    wflow_id = cmd.get_data()['workflow_id']
    title = f'MagicFlow workflow {wflow_id}'
    desc = f'https://api.sview.tenant.manage.cto2b.eu/#!/workflows/{wflow_id}'

    file_path = stage + '/' + environment + '/' + "kubernetes-external-secrets" + '/' + "values.yaml"
    logger.info("Modification will be done to infra-config repository %s" %
                file_path)

    project_id = self._config.get('infra_config_project_id')
    gl = GitlabDriver(self.gitlab_api_token, project_id)

    # get project files
    try:
        f = gl.get_project_file(file_path)
    except gitlab.exceptions.GitlabGetError:
        logger.error("File %s not found in infra-config" % file_path)

    # modify file content if needed
    file_content = base64.b64decode(f.content).decode("utf-8").strip('\n')
    if ns in file_content:
        logger.info("WATCHED_NAMESPACES already contains %s" % ns)
        return {
            "parameters": {
                "mr_created": "False",
                "mr_id": "0",
                "project_id": project_id
            },
            "result": f'`WATCHED_NAMESPACES` already contains `{ns}`'
        }
    else:
        logger.info("WATCHED_NAMESPACES does not contain %s, MR needed" % ns)
        values_yaml = file_content.replace('WATCHED_NAMESPACES: "',
                                           'WATCHED_NAMESPACES: "' + ns + ',')

        f.content = values_yaml

        # push to gitlab
        mr = gl.push_mr(f,
                        branch=job_id,
                        title=title,
                        description=desc,
                        jira_ticket=jira_ticket)

        if mr:
            mr_id = mr["mr_id"]
            mr_url = mr["mr_url"]
            return {
                "output": mr,
                "parameters": {
                    "mr_created": "True",
                    "mr_id": mr_id,
                    "mr_url": mr_url,
                    "project_id": project_id
                },
                "result": f'MR [#{mr_id}]({mr_url}) created'
            }

        return mr.update({
            "parameters": {
                "mr_created": "False",
                "mr_id": "0",
                "project_id": project_id
            }
        })


def _validate_namespace(gitlab, capability, data_service_name,
                        namespaces_values_path, capabilities_values_path):
    """
    Check if namespace is duplicate. Validates following files:
      - <stage>/env-overlays/<environment>/namespaces/values.yaml
      - <stage>/env-overlays/<environment>/capabilities/values.yaml

    Returns:
        If either of files contains already existing namespace function
        returns True.
    """

    logger.info(
        f'Validating if namespace {capability} does not exist in {namespaces_values_path}.'
    )
    f = gitlab.get_project_file(namespaces_values_path)
    file_content = base64.b64decode(f.content).decode('utf-8')

    yml = yaml.safe_load(file_content)
    namespaces = yml.get(data_service_name, {}).get("namespaces", {})
    for ns in namespaces:
        if ns['name'] == capability:
            logger.info(
                f'Duplicate namespace {capability} found in {namespaces_values_path}.'
            )
            return True

    logger.info(
        f'Validating if namespace {capability} does not exist in {capabilities_values_path}.'
    )
    f = gitlab.get_project_file(capabilities_values_path)
    file_content = base64.b64decode(f.content).decode('utf-8')

    yml = yaml.safe_load(file_content)
    namespaces = yml.get(data_service_name, {}).get("namespaces", {})
    for ns in namespaces:
        if ns == capability:
            logger.info(
                f'Duplicate namespace {capability} found in {capabilities_values_path}.'
            )
            return True
    logger.info(f'Duplicate namespace {capability} not found.')
    return False


def create_app_of_apps_namespace(self, cmd: CommandMessage):
    """
        Creates namespaces in following files:
            - <stage>/env-overlays/<environment>/capabilities/values.yaml
            - <stage>/env-overlays/<environment>/namespaces/values.yaml

        Returns:
            Function returns Gitlab ProjectFile if namespace is created successfully.
        """

    input_data = cmd.get_data()["input"]

    stage = input_data['stage']
    jira_ticket = input_data['jira_ticket']
    environment = input_data['environment']
    capability = input_data['namespace']
    data_service_name = input_data['service']
    job_id = cmd.get_data()['job_id']
    wflow_id = cmd.get_data()['workflow_id']
    title = f'MagicFlow workflow {wflow_id}'
    desc = f'https://api.sview.tenant.manage.cto2b.eu/#!/workflows/{wflow_id}'
    namespaces_values_path = f'{stage}/env-overlays/{environment}/namespaces/values.yaml'
    capabilities_values_path = f'{stage}/env-overlays/{environment}/capabilities/values.yaml'

    project_id = self._config.get('app_of_apps_project_id')

    gl = GitlabDriver(self.gitlab_api_token, project_id)

    if _validate_namespace(gl, capability, data_service_name,
                           namespaces_values_path, capabilities_values_path):
        return {
            "parameters": {
                "project_id": project_id,
                "mr_created": "False"
            },
            "result": "No changes needed"
        }

    logger.info(
        f'Creating namespace {capability} in {namespaces_values_path}.')
    ns_values_f = gl.get_project_file(namespaces_values_path)
    file_content = base64.b64decode(ns_values_f.content).decode('utf-8')
    ns_values = yaml.safe_load(file_content)

    # Append YAML block if service exists
    if ns_values.get(data_service_name, {}):
        new_ns = [{
            'name':
            capability,
            'externalSecrets': ['gitlab-registry', 'gitlab-dependency-proxy']
        }]
        ns_values[data_service_name]['namespaces'].extend(new_ns)

    # Create YAML block from scratch if service does not exist
    if not ns_values.get(data_service_name, {}):
        yml_block = {
            data_service_name: {
                'namespaces': [{
                    'name':
                    capability,
                    'externalSecrets':
                    ['gitlab-registry', 'gitlab-dependency-proxy']
                }]
            }
        }
        ns_values.update(yml_block)

    ns_values_f.content = yaml.dump(ns_values,
                                    Dumper=CustomDumper,
                                    sort_keys=False)

    logger.info(
        f'Creating namespace {capability} in {capabilities_values_path}.')
    cap_values_f = gl.get_project_file(capabilities_values_path)
    file_content = base64.b64decode(cap_values_f.content).decode('utf-8')
    ns_values = yaml.safe_load(file_content)

    try:
        if ns_values[data_service_name]['namespaces']:
            ns_values[data_service_name]['namespaces'].append(capability)
    except KeyError:
        ns_values[data_service_name]['namespaces'] = [capability]

    cap_values_f.content = yaml.dump(ns_values,
                                     Dumper=CustomDumper,
                                     sort_keys=False)

    mr = gl.push_mr(ns_values_f,
                    cap_values_f,
                    branch=job_id,
                    title=title,
                    description=desc,
                    jira_ticket=jira_ticket)

    if mr:
        mr_id = mr["mr_id"]
        mr_url = mr["mr_url"]
        return {
            "output": mr,
            "parameters": {
                "mr_created": "True",
                "mr_id": mr_id,
                "mr_url": mr_url,
                "project_id": project_id
            },
            "result": f'MR [#{mr_id}]({mr_url}) created'
        }

    return mr.update({
        "parameters": {
            "mr_created": "False",
            "mr_id": "0",
            "project_id": project_id
        }
    })


def merge(self, cmd: CommandMessage):
    """
        Perform merge request.
        Input:
            mr_iid, project_id

        Returns:
            Function returns result/status.
        """

    # retrieve all input arguments
    try:
        input_data = cmd.get_data()["input"]
        job_id = cmd.get_data()['job_id']
        mr_id = input_data['mr_id']
        project_id = input_data['project_id']
        gl = GitlabDriver(self.gitlab_api_token, project_id)
        do_merge = gl.merge(mr_id)
        return do_merge

    except KeyError as exc:
        logger.error(f'Missing input parameters mr_id, project_id')
        return {"result": f'{exc}'}
