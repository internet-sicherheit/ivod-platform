from django.core.signing import Signer
from django.urls import reverse
from django.utils import baseconv
from pive import environment, inputmanager, outputmanager
from pathlib import Path
import json
import sys
import os
from django.conf import settings

from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend

from django.core import signing
from django.template.loader import render_to_string

def get_chart_types_for_datasource(datasource):
    """Create a list of supported chart types for a datasource
    :param Datasource datasource: The datasource, for which the chart types should be generated
    :return: A list of chart types
    :rtype: [str]
    """

    manager = inputmanager.InputManager(mergedata=False, accept_unordered=getattr(settings, "DATA_ALLOW_UNORDERED", False))
    env = environment.Environment(inputmanager=manager)
    supported = env.load(datasource.source)
    return supported

def render_chart(chart, chart_id, environment, request, config=None):
    """(Re-)draw a chart. Before calling, environment.choose or environment.load_raw should have been called.
    :param Basevisualization chart: The chart object to be rendered
    :param str/int chart_id: The primary key of the chart in the database
    :param Environment environment: The rendering environment of pive
    :param HttpRequest request: Request object of the call that triggered rendering
    :param dict config: Dictionary representing information on how to customize rendering. See pive for more details
    """
    #TODO: Order od operation correct? Should config overwrite html template path?
    #FIXME: Check if chart type is selected
    if config:
        chart.load_from_dict(json.loads(config))
    chart.set_html_template(Path(getattr(settings, "CHART_TEMPLATE", Path(__file__).resolve().parent.joinpath("res").joinpath("default_template.html"))))
    dataset_url = request.build_absolute_uri(reverse("chart-data", kwargs={'pk': chart_id}))
    chart.set_dataset_url(dataset_url)
    config_url = request.build_absolute_uri(reverse("chart-config", kwargs={'pk': chart_id}))
    code_src = request.build_absolute_uri(reverse("chart-code", kwargs={'pk': chart_id}))
    _ = environment.render(chart, template_variables={'t_config_url': config_url, 't_code_src': code_src}, filenames={'chart.js': None})
    _ = environment.render_code(chart)

def generate_chart(datasource, chart_id, chart_type, request, config=None):
    """Generate a new new chart.
    :param Datasource datasource: The datasource to use for rendering this chart
    :param str/int chart_id: The primary key of the chart in the database
    :param str chart_type: The chart type
    :param HttpRequest request: Request object of the call that triggered rendering
    :param dict config: Dictionary representing information on how to customize rendering. See pive for more details
    """

    base_path = get_chart_base_path()
    base_path.mkdir(parents=True, exist_ok=True)
    output_path = base_path.joinpath(str(chart_id))

    manager = inputmanager.InputManager(mergedata=False, accept_unordered=getattr(settings, "DATA_ALLOW_UNORDERED", False))
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    supported = env.load(datasource.source)
    if chart_type not in supported:
        raise Exception("Chart type unsupported")
    chart = env.choose(chart_type)
    render_chart(chart, chart_id, env, request, config)

def modify_chart(chart_id, request, config=None):
    """Modify an existing chart.
    :param str/int chart_id: The primary key of the chart in the database
    :param str chart_type: The chart type
    :param HttpRequest request: Request object of the call that triggered rendering
    :param dict config: Dictionary representing information on how to customize rendering. See pive for more details
    """

    base_path = get_chart_base_path()
    base_path.mkdir(parents=True, exist_ok=True)
    output_path = base_path.joinpath(str(chart_id))

    persisted_data_path = output_path.joinpath("persisted.json")
    with Path(persisted_data_path).open("r") as persisted_data_file:
        persisted_data = json.load(persisted_data_file)
    manager = inputmanager.InputManager(mergedata=False, accept_unordered=getattr(settings, "DATA_ALLOW_UNORDERED", False))
    env = environment.Environment(inputmanager=manager, outputmanager=outputmanager.FolderOutputManager(output_path))
    chart = env.load_raw(persisted_data)
    render_chart(chart, chart_id, env, request, config)

def get_datasource_base_path():
    """Get a Path object pointing to the base directory containing datasources"""
    TESTING = 'test' in sys.argv
    if TESTING:
        if os.name == 'nt':
            return Path(os.environ["TEMP"]).joinpath("ivod-platform-test")
        else:
            return Path("/tmp/ivod-platform-test/datasources")
    else:
        return Path(getattr(settings, "DATASOURCE_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("datasource_data")))

def get_chart_base_path():
    """Get a Path object pointing to the base directory containing chart data"""
    TESTING = 'test' in sys.argv
    if TESTING:
        if os.name == 'nt':
            return Path(os.environ["TEMP"]).joinpath("ivod-platform-test")
        else:
            return Path("/tmp/ivod-platform-test/charts")
    else:
        return Path(getattr(settings, "CHART_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("chart_data")))

def get_code_base_path():
    """Get a Path object pointing to the base directory containing js code"""
    TESTING = 'test' in sys.argv
    if TESTING:
        if os.name == 'nt':
            return Path(os.environ["TEMP"]).joinpath("ivod-platform-test")
        else:
            return Path("/tmp/ivod-platform-test/code")
    else:
        return Path(getattr(settings, "JS_BASE_PATH", Path(__file__).resolve().parent.parent.joinpath("code")))

def get_config_for_chart(chart):
    """Get the complete config object for a chart."""
    with get_chart_base_path().joinpath(str(chart.id)).joinpath('config.json').open('r') as file:
        config = json.load(file)
        return config

def send_a_mail(receiver, subject, content, html_content=None):
    try:
        return 1 == send_mail(
            subject=subject,
            message=content,
            from_email=getattr(settings, "EMAIL_SENDING_ADDRESS"),
            recipient_list=[receiver],
            html_message=html_content,
            connection=EmailBackend()
        )
    except Exception as e:
        return False

def send_verification_mail(user, email, request):
    # Create a token for user with specified new e-mail
    serialized_id = signing.dumps(
        {'user': user.id.hex, 'token_type': "EMAIL_CHANGE", 'email': email}
    )

    # Build a verification mail from templates
    context = {
        'title': 'Verify your mail address',
        'token': serialized_id,
        'confirmation_url': request.build_absolute_uri(
            reverse("confirm_email", kwargs={'token': serialized_id}))
    }
    text_content = render_to_string('platformAPI/mail_change_text.jinja2', context=context, request=request)
    html_content = render_to_string('platformAPI/mail_change_html.jinja2', context=context, request=request)

    send_a_mail(email, context['title'], text_content, html_content=html_content)

def get_timestamp_from_token(token):
    # Functionality should be the same as django.core.signing.TimestampSigner
    try:
        signer = Signer()
        result = signer.unsign(token)
        return baseconv.base62.decode(
            result.rsplit(signer.sep, 1)[1]
        )
    except:
        return None
