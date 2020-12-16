from pive import environment, inputmanager, outputmanager
from pathlib import Path
import json
import sys

def get_chart_types_for_datasource(datasource):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager)
    supported = env.load(datasource.source)
    return supported

def generate_chart(datasource, chart_type, output_path, config=None):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    supported = env.load(datasource.source)
    if chart_type not in supported:
        raise Exception("Chart type unsupported")
    chart = env.choose(chart_type)
    if config:
        chart.load_from_dict(json.loads(config))
    #FIXME: specify correct dataset URL
    chart.set_dataset_url(f"./{chart_type}.json")
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

def get_chart_base_path():
    #TODO: Get paths from config
    TESTING = 'test' in sys.argv
    if TESTING:
        #FIXME: Get TMP path for windows systems
        return Path("/tmp").resolve().joinpath("chart_data")
    else:
        return Path(__file__).resolve().parent.parent.joinpath("chart_data")