from django.apps import AppConfig
from pive.environment import Environment
from .util import get_code_base_path

from pathlib import Path

import pive

class PlatformapiConfig(AppConfig):
    name = 'platformAPI'

    def ready(self):
        visualisations = Environment.import_all_visualisations()
        get_code_base_path().mkdir(parents=True, exist_ok=True)
        with Path(pive.__file__).parent.joinpath("visualization").joinpath("static").joinpath("base.js").open("r") as infile:
            with get_code_base_path().joinpath("base.js").open("w") as outfile:
                outfile.write(infile.read())
        # Update visualisation JS code to the newest version
        # Keep older version
        for name in visualisations:
            version = visualisations[name].get_version()
            folder = get_code_base_path().joinpath(version)
            folder.mkdir(parents=True, exist_ok=True)
            with folder.joinpath(f"{name}.js").open("w") as outfile:
                outfile.write(visualisations[name].get_js_code())
