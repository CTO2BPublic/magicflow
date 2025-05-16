from google.cloud import secretmanager_v1
from google import auth
from loguru import logger
import re

def list_parameters(stage, environment):
    client = secretmanager_v1.SecretManagerServiceClient()
    project_id = auth.default()[1]

    logger.debug(f'Getting all parameters in {project_id} (stage: {stage}, environment: {environment})')
    # List all secrets based on the filter
    request = secretmanager_v1.ListSecretsRequest(
        parent=f"projects/{project_id}",
    )
    secrets = client.list_secrets(request=request)

    # Get the latest version for each existing secret
    output = []
    for secret in secrets:
        if f'_app_' in secret.name:
            output.append(re.sub(r'^projects/[^/]+/secrets/', '', secret.name))

    return output

def get_parameter(stage, environment, namespace, name):
    client = secretmanager_v1.SecretManagerServiceClient()
    project_id = auth.default()[1]

    logger.debug(f'Getting parameter: {namespace}_app_{name}_* in {project_id} (stage: {stage}, environment: {environment})')
    # List all secrets based on the filter
    request = secretmanager_v1.ListSecretsRequest(
        parent=f"projects/{project_id}",
    )
    secrets = client.list_secrets(request=request)

    # Get the latest version for each existing secret
    output = {}
    for secret in secrets:
        if f'secrets/{namespace}_app_{name}_' in secret.name:
            sname = f"{secret.name}/versions/latest"
            response = client.access_secret_version(name=sname)
            expr = r'^projects/[^/]+/secrets/' + re.escape(namespace) + r'_app_' + re.escape(name) + r'_'
            output[re.sub(expr, '', secret.name)] = response.payload.data.decode('UTF-8')

    return output


def update_parameter(value, stage, environment, namespace, name, rewrite=False):
    existing_value = get_parameter(stage, environment, namespace, name)

    for k, v in value.items():
        if k not in existing_value:
            logger.debug(f'Key {k} is not the existing secret - creating')
            existing_value[k] = v
            _create_secret(k, v, stage, environment, namespace, name)
        elif existing_value[k] != v:
            logger.debug(f'Key {k} is is not the same value as existing secret - replacing')
            existing_value[k] = v
            _update_secret(k, v, environment, namespace, name)
        else:
            if rewrite:
                logger.debug(f'Creating new secret, or rewriting existing due to --rewrite option')
                existing_value[k] = v
                _update_secret(k, v, environment, namespace, name)
            else:
                logger.debug(f'Key {k} is the same in the existing secret - skipping')
        logger.debug(f'Updated parameter: {k}')


    return True

def _create_secret(key, value, stage, environment, namespace, name):
    secret_id = f"{namespace}_app_{name}_{key}"
    project_id = auth.default()[1]
    secret_name = f"projects/{project_id}/secrets/{secret_id}"
    client = secretmanager_v1.SecretManagerServiceClient()
    secret = secretmanager_v1.Secret(name=secret_name)

    payload = secretmanager_v1.SecretPayload(data=value.encode("UTF-8"))

    secret.replication = {
            "automatic": {
                "customer_managed_encryption": secretmanager_v1.CustomerManagedEncryption(
                    kms_key_name=f'projects/{environment}/locations/global/keyRings/data-keyring-global/cryptoKeys/data-key'
                )
            }
        }
    secret.labels = {
        "stage": stage,
        "environment": environment,
        "namespace": namespace,
        "instance": name,
        "capability": "app-secret"
    }

    client.create_secret(
        parent=f"projects/{project_id}", secret_id=secret_id, secret=secret
    )
    client.add_secret_version(parent=secret_name, payload=payload)
    return True

def _update_secret(key, value, environment, namespace, name):
    secret_id = f"{namespace}_app_{name}_{key}"
    project_id = auth.default()[1]
    secret_name = f"projects/{project_id}/secrets/{secret_id}"
    client = secretmanager_v1.SecretManagerServiceClient()
    payload = secretmanager_v1.SecretPayload(data=value.encode("UTF-8"))
    client.add_secret_version(parent=secret_name, payload=payload)
