from pive import environment, inputmanager
import json

def get_chart_types_for_datasource(datasource):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager)
    supported = env.load(datasource.source)
    return supported

def generate_chart(datasource, chart_type, output_path, config=None):
    manager = inputmanager.InputManager(mergedata=False)
    env = environment.Environment(inputmanager=manager, outputpath=output_path)
    supported = env.load(datasource.source)
    if chart_type not in supported:
        raise Exception("Chart type unsupported")
    chart = env.choose(chart_type)
    if config:
        chart.load_from_dict(json.loads(config))
    chart.set_dataset_url(f"./{chart_type}.json")
    _ = env.render(chart)
    _ = env.render_code(chart)