import yaml

## CustomDumper is used to dump the yaml file with blank lines between top-level objects.
## Neither PyYAML or ruamel.yaml supports this
class CustomDumper(yaml.SafeDumper):
    """ 
    Insert blank lines between top-level objects.
    Neither PyYAML or ruamel.yaml supports this
    """
    def write_line_break(self, data=None):
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()
