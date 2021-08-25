from django.apps import AppConfig
from pive.environment import Environment
from .util import get_code_base_path

from django.db.utils import IntegrityError

import os
from sys import stderr

from pathlib import Path

import pive

class PlatformapiConfig(AppConfig):
    name = 'platformAPI'

    def ready(self):

        if os.environ.get("RUN_SERVER") is not None:
            # Generate boot users
            from django.conf import settings
            from .models import User
            from django.core.exceptions import ObjectDoesNotExist
            
            boot_users = getattr(settings, "BOOT_USERS", [])
            for b_user in boot_users:
                try:
                    new_user = User.objects.create_user(email=b_user['email'], username=b_user['username'], password=b_user['password'])
                except IntegrityError as error:
                    # Race condition during insertion or user already in DB before, ignore
                    pass
                except Exception as e:
                    # Another error occured, such as malformed user. Report and continue
                    print(e, file=stderr)


        # Generate visualistion files
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
