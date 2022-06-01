from . import version

from .sketch.sketch import Sketch
from .synthesizers.synthesizer import *
from .synthesizers.synthesizer_pomdp import SynthesizerPOMDP

import click
import sys
import os

import logging
# logger = logging.getLogger(__name__)

def setup_logger(log_path = None):
    ''' Setup routine for logging. '''
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # root.setLevel(logging.INFO)

    # formatter = logging.Formatter('%(asctime)s %(threadName)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(filename)s - %(message)s')

    handlers = []
    if log_path is not None:
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        handlers.append(fh)
    sh = logging.StreamHandler(sys.stdout)
    handlers.append(sh)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(formatter)
    for h in handlers:
        root.addHandler(h)
    return handlers


@click.command()
@click.option("--project", required=True, help="project path", )

@click.option("--sketch", default="sketch.templ", show_default=True,
    help="name of the sketch file in the project")
@click.option("--props", default="sketch.props", show_default=True,
    help="name of the properties file in the project")
@click.option("--constants", default="", help="constant assignment string", )

@click.option("--filetype",
    type=click.Choice(['prism', 'drn', 'pomdp']),
    default="prism", show_default=True,
    help="input file format")
@click.option("--export",
    type=click.Choice(['drn', 'pomdp']),
    help="export the model to *.drn/*.pomdp and abort")

@click.option("--method",
    type=click.Choice(['onebyone', 'ar', 'cegis', 'hybrid']),
    default="ar", show_default=True,
    help="synthesis method"
    )
@click.option("--incomplete-search", is_flag=True, default=False,
    help="use incomplete search during synthesis")
@click.option("--fsc-synthesis", is_flag=True, default=False,
    help="enable incremental synthesis of FSCs for a POMDP")
@click.option("--pomdp-memory-size", default=1, show_default=True,
    help="implicit memory size for POMDP FSCs")
@click.option("--hyperproperty", is_flag=True, default=False,
    help="enable synthesis of an MDP scheduler wrt a hyperproperty")

def paynt(
        project,
        sketch, props, constants,
        filetype, export,
        method,
        incomplete_search, fsc_synthesis, pomdp_memory_size,
        hyperproperty
):
    logger.info("This is Paynt version {}.".format(version()))

    # set CLI parameters
    Synthesizer.incomplete_search = incomplete_search
    POMDPQuotientContainer.initial_memory_size = pomdp_memory_size
    Sketch.hyperproperty_synthesis = hyperproperty

    # check paths of input files
    sketch_path = os.path.join(project, sketch)
    properties_path = os.path.join(project, props)
    if not os.path.isdir(project):
        raise ValueError(f"The project folder {project} does not exist")
    if not os.path.isfile(sketch_path):
        raise ValueError(f"The sketch file {sketch_path} does not exist")
    if not os.path.isfile(properties_path):
        raise ValueError(f"The properties file {properties_path} does not exist")
    
    # parse sketch
    sketch = Sketch(sketch_path, filetype, export, properties_path, constants)

    # choose the synthesis method and run the corresponding synthesizer
    if sketch.is_pomdp and fsc_synthesis:
        synthesizer = SynthesizerPOMDP(sketch, method)
    elif method == "onebyone":
        synthesizer = Synthesizer1By1(sketch)
    elif method == "ar":
        synthesizer = SynthesizerAR(sketch)
    elif method == "cegis":
        synthesizer = SynthesizerCEGIS(sketch)
    elif method == "hybrid":
        synthesizer = SynthesizerHybrid(sketch)
    else:
        pass
    synthesizer.run()


def main():
    setup_logger()
    paynt()


if __name__ == "__main__":
    main()
