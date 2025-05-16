import json
class Metadata:
    _instance = None

    def __init__(self, **kwargs):
        # Initialize metadata values here
        self._metadata = kwargs

    def get(self, key):
        return self._metadata.get(key)

    def set(self, key, value):
        self._metadata[key] = value
        return self

    def has(self, key):
        return key in self._metadata

    def validate(self, keys: list) -> dict:
        missing = []
        for key in keys:
            if key not in self._metadata or not self._metadata[key]:
                missing.append(key)

        if len(missing) > 0:
          return {
              "result": "Missing metadata keys",
              "error": json.dumps({
                  "message": "Missing metadata keys",
                  "missing_keys": missing
              }, indent=4)
          }
        return None

    @classmethod
    def get_instance(cls, **kwargs):
        if not cls._instance:
            cls._instance = Metadata(**kwargs)
        return cls._instance
