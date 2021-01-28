from django.apps import AppConfig
from pive.environment import Environment
from pathlib import Path
from django.conf import settings

class PlatformapiConfig(AppConfig):
    name = 'platformAPI'

    def ready(self):
        visualisations = Environment.import_all_visualisations()
        # Update visualisation JS code to the newest version
        # Keep older version
        for name in visualisations:
            version = visualisations[name].get_version()
            folder = Path(getattr(settings, "JS_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("code"))).joinpath(version)
            folder.mkdir(exist_ok=True)
            with folder.joinpath(f"{name}.js").open("w") as outfile:
                outfile.write(visualisations[name].get_js_code())
