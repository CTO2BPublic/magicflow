import boto3
from magicflow.libs import dict_values_to_string
import json
from loguru import logger

def list_parameters(stage, environment):
    ssm = boto3.client('ssm')
    parameters = []
    paginator = ssm.get_paginator('describe_parameters')
    for page in paginator.paginate(ParameterFilters=[
        {
            'Key': 'Name',
            'Option': 'BeginsWith',
            'Values': [f'/{stage}/{environment}/']
        },
    ]):
        for param in page['Parameters']:
            parameters.append(param['Name'])

    return parameters

def get_parameter(stage, environment, namespace, name):
    ssm = boto3.client('ssm')
    try:
        parameter_name = f'/{stage}/{environment}/{namespace}/application-secrets-{name}'
        logger.debug(f'Getting parameter: {parameter_name}')
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        if response['Parameter'] and response['Parameter']['Value']:
            return json.loads(response['Parameter']['Value'])

        return None
    except ssm.exceptions.ParameterNotFound:
        logger.debug(f'Parameter not found: {parameter_name}')
        return None

def update_parameter(value, stage, environment, namespace, name, rewrite=False):

    ssm = boto3.client('ssm')
    parameter_name = f'/{stage}/{environment}/{namespace}/application-secrets-{name}'
    logger.debug(f'Updating parameter: {parameter_name}')
    existing_value = get_parameter(stage, environment, namespace, name)
    if existing_value and not rewrite:
        logger.debug(f'Secret already exists: {parameter_name}')
        for k, v in value.items():
            if k not in existing_value or existing_value[k] != v:
                logger.debug(f'Key {k} is different in the existing secret - replacing')
                existing_value[k] = v
            else:
                logger.debug(f'Key {k} is the same in the existing secret - skipping')
        value = existing_value
    else:
        logger.debug(f'Creating new secret, or rewriting existing due to --rewrite option')

    ssm.put_parameter(
        Name=parameter_name,
        Value=json.dumps(dict_values_to_string(value)),
        Type='SecureString',
        Overwrite=True,
        KeyId=f'alias/{stage}-{environment}-data',
    )

    return True
