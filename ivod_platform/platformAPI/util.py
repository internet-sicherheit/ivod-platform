from django.urls import reverse
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

def render_chart(chart, chart_id, environment, request, config=None):
    #TODO: Order od operation correct? Should config overwrite html template path?
    if config:
        chart.load_from_dict(json.loads(config))
    chart.set_html_template(Path(getattr(settings, "CHART_TEMPLATE", Path(__file__).resolve().parent.joinpath("res").joinpath("default_template.html"))))
    dataset_url = request.build_absolute_uri(reverse("chart-data", kwargs={'pk': chart_id}))
    chart.set_dataset_url(dataset_url)
    config_url = request.build_absolute_uri(reverse("chart-config", kwargs={'pk': chart_id}))
    code_src = request.build_absolute_uri(reverse("chart-code", kwargs={'pk': chart_id}))
    _ = environment.render(chart, template_variables={'t_config_url': config_url, 't_code_src': code_src}, filenames={'chart.js': None})
    _ = environment.render_code(chart)

def generate_chart(datasource, chart_id, chart_type, output_path, request, config=None):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    supported = env.load(datasource.source)
    if chart_type not in supported:
        raise Exception("Chart type unsupported")
    chart = env.choose(chart_type)
    render_chart(chart, chart_id, env, request, config)

def modify_chart(chart_id, output_path, request, config=None):
    persisted_data_path = get_chart_base_path().joinpath(str(chart_id)).joinpath("persisted.json")
    with Path(persisted_data_path).open("r") as persisted_data_file:
        persisted_data = json.load(persisted_data_file)
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    chart = env.load_raw(persisted_data)
    render_chart(chart, chart_id, env, request, config)

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

def get_code_base_path():
    TESTING = 'test' in sys.argv
    if TESTING:
        if os.name == 'nt':
            return Path(os.environ["TEMP"]).joinpath("ivod-platform-test")
        else:
            return Path("/tmp/ivod-platform-test/code")
    else:
        return Path(getattr(settings, "JS_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("code")))

def get_config_for_chart(chart):
    """Get the complete config object for a chart. This takes the base config and updates it with the config saved in the chart object"""
    with get_chart_base_path().joinpath(str(chart.id)).joinpath('config.json').open('r') as file:
        config = json.load(file)
        config.update(json.loads(chart.config))
        return config