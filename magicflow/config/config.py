import os

from dynaconf import Dynaconf

_config_path = os.path.dirname(os.path.realpath(__file__))

settings = Dynaconf(
    envvar_prefix="APP",
    settings_files=["%s/settings.toml" % _config_path,
                    "%s/.secrets.toml" % _config_path],
    environments=True,
    load_dotenv=True,
    env_switcher="APP_ENV",
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
