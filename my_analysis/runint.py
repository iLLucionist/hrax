# !!!
# TO DROP INTO A PYTHON SHELL (IPYTHON), RUN FROM HERE:
#
# (You will have the results to inspect and inquire, but not the reports
#  generated).
# !!!

from importlib import reload

from nowpipes import Pipeline

from helpers import sanitize_filename, reload_modules
from analysis import results, output_files, output_dataset
from reports import setup

import config
import args


# TODO: refactor so that it can handle multiple nestings


# (Re)load modules
reload_modules(['analysis', 'reports'])
reload(config)

# Parse commandline arguments
# params = args.parser.parse_args()

# Make the data pipeline
data = Pipeline()
data.config(
    outputdir=config.outputdir
)

data.add(results)
# Compute results
# UNCOMMENT NEXT LINE TO GENERATE EXCEL DUMP:
# data.add(output_files)
# UNCOMMENT NEXT LINE TO GENERATE DUMP DATASET:
# data.add(output_dataset)
data.run(verbose=True)
r = data.results

# !!!
# TO HERE
# !!
