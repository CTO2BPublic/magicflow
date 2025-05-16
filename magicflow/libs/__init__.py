def dict_values_to_string(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            dictionary[key] = dict_values_to_string(value)
        elif isinstance(value, list):
            dictionary[key] = [str(x) for x in value]
        else:
            dictionary[key] = str(value)
    return dictionary

def print_yaml_dependency(namespace, name, value):
    print(f'========= YAML: {namespace} / {name} =====')
    print('  ssm:')
    print('    keys:')
    for key in value.keys():
        print(f'      - {key}')
    print(f'    instance: {name}')
    print(f'    namespace: {namespace}')
    print("========= YAML =====")
