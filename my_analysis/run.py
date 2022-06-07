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
params = args.parser.parse_args()

# Make the data pipeline
data = Pipeline()
data.config(
    outputdir=config.outputdir
)

data.add(results)
if params.dodump:
    data.add(output_files)
if params.dodataset:
    data.add(output_dataset)

# Compute results
# data.add(output_files)
# data.add(output_dataset)
data.run(verbose=True)
r = data.results

# Make the reports pipeline
reports = Pipeline()
reports_config = config.reports | dict(
    results=r,
    sanitize=sanitize_filename
)
reports.config(**reports_config)
reports.add(setup)
if 'org' in params.nestings:
    from reports import org_report, write_org_report
    reports.add(org_report, write_org_report)
if 'team' in params.nestings:
    from reports import team_reports, write_team_reports
    reports.add(team_reports, write_team_reports)
if 'functie' in params.nestings:
    from reports import functie_reports, write_functie_reports
    reports.add(functie_reports, write_functie_reports)
if 'unit' in params.nestings:
    from reports import unit_reports, write_unit_reports
    reports.add(unit_reports, write_unit_reports)
if 'onderdeel' in params.nestings:
    from reports import onderdeel_reports, write_onderdeel_reports
    reports.add(onderdeel_reports, write_onderdeel_reports)

# Make reports
reports.run(verbose=True)
