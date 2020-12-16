from pive import environment, inputmanager, outputmanager
from pathlib import Path
import json
import sys
import os
from django.conf import settings

def get_chart_types_for_datasource(datasource):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager)
    supported = env.load(datasource.source)
    return supported

def generate_chart(datasource, chart_id, chart_type, output_path, config=None):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    supported = env.load(datasource.source)
    if chart_type not in supported:
        raise Exception("Chart type unsupported")
    chart = env.choose(chart_type)
    if config:
        chart.load_from_dict(json.loads(config))
    dataset_base_url = getattr(settings, "DATASET_BASE_URL", "./")
    #Append leading slash
    if dataset_base_url[-1] != '/':
        dataset_base_url += '/'
    #TODO: Change format of dataset url to omit chart type
    chart.set_dataset_url(f"{dataset_base_url}{chart_id}/{chart_type}.json")
    _ = env.render(chart)
    _ = env.render_code(chart)

def modify_chart(persisted_data_path, output_path, config_string):
    with Path(persisted_data_path).open("r") as persisted_data_file:
        persisted_data = json.load(persisted_data_file)
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    chart = env.load_raw(persisted_data)
    chart.load_from_dict(json.loads(config_string))
    _ = env.render(chart)
    _ = env.render_code(chart)

def get_datasource_base_path():
    TESTING = 'test' in sys.argv
    if TESTING:
        if os.name == 'nt':
            return Path(os.environ["TEMP"]).joinpath("ivod-platform-test")
        else:
            return Path("/tmp/ivod-platform-test/datasources")
    else:
        return Path(getattr(settings, "DATASOURCE_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("datasource_data")))

def get_chart_base_path():
    #Currently unused, planned to point to storage of cached datasources
    TESTING = 'test' in sys.argv
    if TESTING:
        if os.name == 'nt':
            return Path(os.environ["TEMP"]).joinpath("ivod-platform-test")
        else:
            return Path("/tmp/ivod-platform-test/charts")
    else:
        return Path(getattr(settings, "CHART_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("chart_data")))