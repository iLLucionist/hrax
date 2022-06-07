from nowslides import load_yaml, render_presentation
from nowpipes import pipe
from weasyprint import HTML
from importlib import reload
from helpers import (make_str_date, make_report_fname, isinteractive,
                     make_org_report_fname)
from concurrent.futures import (ThreadPoolExecutor, ProcessPoolExecutor,
                                as_completed)
from copy import deepcopy

from zipfile import ZipFile
from os.path import basename

import logging
import os


def make_report(results, prefix, nesting, no, y, elparsers, doprev=False,
                prev_mark=False, prev_mark_delta=0.5):
    """
    Generate HTML reports for the specified number (row) in the nesting.

    Arguments:
    results -- the object containing the analysis results
    prefix -- A string that will be prefixed to the title of the report
    nesting -- The nesting for which to make the report
    no -- The number (row) of the nesting entry to make the report for
    y -- the YAML report specification
    elparsers -- a dict with custom element parsers
    doprev -- Whether previous comparison values should be retrieved
    """
    from entities import (get_response, get_scores, get_summary, get_advice,
                          get_prev_scores, get_advice_by_dvcluster)

    # Variables that are provided to render the report
    variables = {
        'title': "Employee research",
        'prefix': prefix,
        'response': get_response(results, nesting, no),
        'scores': get_scores(results, nesting, no),
        'high_dvs': get_summary(results, nesting, no, 'dvs', 'high'),
        'low_dvs': get_summary(results, nesting, no, 'dvs', 'low'),
        'high_ivs': get_summary(results, nesting, no, 'ivs', 'high'),
        'low_ivs': get_summary(results, nesting, no, 'ivs', 'low'),
        'advice': get_advice(results, nesting, no),
        'advice_by_dvcluster': get_advice_by_dvcluster(results, nesting, no)
    }

    # Add previous scores if requested
    if doprev:
        variables['prev'] = get_prev_scores(results, nesting, no)
        variables['prev_mark'] = prev_mark
        variables['prev_mark_delta'] = prev_mark_delta

    # Render the actual presentation
    html = render_presentation(y, variables, elparsers)

    # The resulting report information
    report = {
        'title': variables['title'],
        'nesting': nesting,
        'value': variables['response']['value'],
        'no': no,
        'html': html
    }

    return report


def make_org_report(results, y, elparsers, doprev=False):
    """
    Generate HTML report for the organization level results.

    Arguments:
    results -- the object containing the analysis results
    y -- the YAML report specification
    elparsers -- a dict with custom element parsers
    doprev -- Whether previous comparison values should be retrieved
    """
    from entities import (get_org_response, get_org_scores,
                          get_org_summary, get_ivstats,
                          get_org_prev_scores,
                          get_org_advice_for_dvclusters)

    # Variables that are provided to render the report
    variables = {
        'title': "Employee research",
        'prefix': "",
        'response': get_org_response(results),
        'scores': get_org_scores(results),
        'high_dvs': get_org_summary(results, 'dvs', 'high'),
        'low_dvs': get_org_summary(results, 'dvs', 'low'),
        'high_ivs': get_org_summary(results, 'ivs', 'high'),
        'low_ivs': get_org_summary(results, 'ivs', 'low'),
        'ivstats': get_ivstats(results),
        'advice_by_dvcluster': get_org_advice_for_dvclusters(results)
    }

    # Add previous scores if requested
    if doprev:
        variables['prev'] = get_org_prev_scores(results)

    # Render the actual presentation
    html = render_presentation(y, variables, elparsers)

    # The resulting report information
    report = {
        'title': variables['title'],
        'html': html
    }

    return report


def write_report(report, nesting, fpath):
    """
    Write HTML report to PDF file for provided report.

    Arguments:
    report: the report dictionary (from make_report())
    nesting: the name of the nesting to write the report for
    fpath: the directory where the file should be written
    """
    # The number of the report
    no = report.no
    # The name of the entity value (e.g., team name)
    value = report.value
    # The filename of the pdf file
    fname = make_report_fname(nesting, no, value)
    fullfname = fpath + fname + '.pdf'
    print(f"  Making PDF #{no} for {fname}", end="\r")
    # Use weasyprint to generate pdf file and write to disk
    html = HTML(string=report.html, base_url="")
    html.write_pdf(fullfname)


def write_reports_for_nesting(reports, nesting, fpath, sanitize, multiproc=2,
                              Executor=ThreadPoolExecutor):
    # Make filename for the zipfile and directory
    dt = make_str_date()
    zipf = fpath + nesting + '_' + dt
    fpath = zipf + '/'
    zipf += '.zip'
    print(f"  Making PDFs for '{nesting}', writing to: {fpath}")

    # Make directory if not exists
    if os.path.exists(fpath) is False:
        print("    -> Making directory")
        os.makedirs(fpath)

    # Render HTML reports to PDF and write to disk
    with Executor(max_workers=multiproc) as executor:
        futures = []
        for report in reports.values():
            futures.append(executor.submit(write_report,
                                           report=deepcopy(report),
                                           nesting=deepcopy(nesting),
                                           fpath=deepcopy(fpath)))
        for future in as_completed(futures):
            pass

    print()
    print(f"  Zipping to: {zipf}")
    # Make zip archive for reports
    with ZipFile(zipf, 'w') as zipobj:
        for dirname, subdirs, fnames in os.walk(fpath):
            for fname in fnames:
                fullfile = os.path.join(dirname, fname)
                zipobj.write(fullfile, basename(fullfile))

    print("\n  Zipping DONE!\n")
    print(f"  PDFs for '{nesting}' in: {fpath}")
    print("")


@pipe
def setup(**p):
    """
    Initialize the reports pipeline
    """
    import nowslides
    import elparsers

    reload(elparsers)
    reload(nowslides)

    # Set the template path from configuration
    nowslides.set_template_path(p.get('tpldir', './templates/'))

    # Make sure weasyprint logs to disk and not to sdtout
    logfile = p.get('weasylog', 'weasyprint.log')
    logger = logging.getLogger('weasyprint')
    logger.handler = []
    logger.addHandler(logging.FileHandler(logfile))
    logger.setLevel(100)

    # See which executor to use
    if isinteractive():
        print("!!! Using threads")
        executor = ThreadPoolExecutor
    else:
        print("!!! Using processes")
        executor = ProcessPoolExecutor

    # Return setup data
    return {
        # Threads or Processes
        'executor': executor,
        # Custom element parsers for template rendering
        'elparsers': elparsers.elparsers,
        # The respective YAML presentations to use for template rendering
        'y_team': load_yaml('./assets/yaml/_team.yaml'),
        'y_functie': load_yaml('./assets/yaml/functie.yaml'),
        'y_unit': load_yaml('./assets/yaml/unit.yaml'),
        'y_onderdeel': load_yaml('./assets/yaml/onderdeel.yaml'),
        'y_org': load_yaml('./assets/yaml/org.yaml')
    }


@pipe
def team_reports(setup, **p):
    """
    Generate HTML team reports based on computed results.
    """
    r = dict()

    # The YAML presentation format
    y = setup.y_team
    # The custom element parsers
    elparsers = setup.elparsers
    # The team prefix
    prefix = 'Team: '

    # Get information for the team nesting
    nesting = p['results'].nesting['team']
    # Retrieve where there are previous scores to process
    doprev = p.get('prev', False)
    prev_mark = p.get('prev_mark', False)
    prev_mark_delta = p.get('prev_mark_delta', 0.5)

    # Only make reports for teams that have a minimum of 5 members.
    team_nos = nesting[nesting.n >= p.get('min_team_size', 5)].index

    # Make the actual HTML reports
    for team_no in team_nos:
        per = round((float(team_no) / max(team_nos)) * 100)
        print(f"Rendering team presentations #{team_no} ({per}%)..", end="\r")
        r[team_no] = make_report(p['results'], prefix, 'team', team_no,
                                 y, elparsers, doprev,
                                 prev_mark, prev_mark_delta)

    print("")

    return r


@pipe
def functie_reports(setup, **p):
    """
    Generate HTML functie reports based on computed results.
    """
    r = dict()

    # The YAML presentation format
    y = setup.y_functie
    # The custom element parsers
    elparsers = setup.elparsers
    # The functie prefix
    prefix = 'Functie: '

    # Get information for the team nesting
    nesting = p['results'].nesting['functie']
    # Retrieve where there are previous scores to process
    doprev = p.get('prev', False)

    # Only make reports for teams that have a minimum of 5 members.
    functie_nos = nesting[nesting.n >= p.get('min_functie_size', 5)].index

    # Make the actual HTML reports
    for functie_no in functie_nos:
        per = round((float(functie_no) / max(functie_nos)) * 100)
        print(f"Rendering functie presentations #{functie_no} ({per}%)..",
              end="\r")
        r[functie_no] = make_report(p['results'], prefix, 'functie',
                                    functie_no, y, elparsers, doprev)

    print("")

    return r


@pipe
def unit_reports(setup, **p):
    """
    Generate HTML unit reports based on computed results.
    """
    r = dict()

    # The YAML presentation format
    y = setup.y_unit
    # The custom element parsers
    elparsers = setup.elparsers
    # The functie prefix
    prefix = 'Divisie: '

    # Get information for the unit nesting
    nesting = p['results'].nesting['unit']
    # Retrieve where there are previous scores to process
    doprev = p.get('prev', False)

    # Only make reports for units that have a minimum of 5 members.
    unit_nos = nesting[nesting.n >= p.get('min_unit_size', 5)].index

    # Make the actual HTML reports
    for unit_no in unit_nos:
        per = round((float(unit_no) / max(unit_nos)) * 100)
        print(f"Rendering unit presentations #{unit_no} ({per}%)..",
              end="\r")
        r[unit_no] = make_report(p['results'], prefix, 'unit',
                                 unit_no, y, elparsers, doprev)

    print("")

    return r


@pipe
def onderdeel_reports(setup, **p):
    """
    Generate HTML onderdeel reports based on computed results.
    """
    r = dict()

    # The YAML presentation format
    y = setup.y_onderdeel
    # The custom element parsers
    elparsers = setup.elparsers
    # The functie prefix
    prefix = 'Onderdeel: '

    # Get information for the onderdeel nesting
    nesting = p['results'].nesting['onderdeel']
    # Retrieve where there are previous scores to process
    doprev = p.get('prev', False)

    # Only make reports for onderdeel that have a minimum of 5 members.
    onderdeel_nos = nesting[nesting.n >= p.get('min_onderdeel_size', 5)].index

    # Make the actual HTML reports
    for onderdeel_no in onderdeel_nos:
        per = round((float(onderdeel_no) / max(onderdeel_nos)) * 100)
        print(f"Rendering onderdeel presentations #{onderdeel_no} ({per}%)..",
              end="\r")
        r[onderdeel_no] = make_report(p['results'], prefix, 'onderdeel',
                                 onderdeel_no, y, elparsers, doprev)

    print("")

    return r


@pipe
def org_report(setup, **p):
    """
    Generate HTML org report based on computed results.
    """
    # The YAML presentation format
    y = setup.y_org
    # The custom element parsers
    elparsers = setup.elparsers
    # Retrieve where there are previous scores to process
    doprev = p.get('prev', False)
    # Make the actual HTML report
    return make_org_report(p['results'], y, elparsers, doprev)


@pipe
def write_team_reports(setup, team_reports, **p):
    """
    Generate team reports to PDF and write to disk
    """
    fpath = p.get('outputdir', './output/')
    # Get number of cores to use
    multiproc = p.get('multiproc', 2)
    # Function to remove characters from nesting names that cannot be
    # used for filenames
    sanitize = p['sanitize']
    executor = setup.executor
    write_reports_for_nesting(team_reports, 'team', fpath, sanitize,
                              multiproc, Executor=executor)


@pipe
def write_functie_reports(setup, functie_reports, **p):
    """
    Generate functie reports to PDF and write to disk
    """
    fpath = p.get('outputdir', './output/')
    # Get number of cores to use
    multiproc = p.get('multiproc', 2)
    # Function to remove characters from nesting names that cannot be
    # used for filenames
    sanitize = p['sanitize']
    executor = setup.executor
    write_reports_for_nesting(functie_reports, 'functie', fpath, sanitize,
                              multiproc, Executor=executor)


@pipe
def write_unit_reports(setup, unit_reports, **p):
    """
    Generate functie reports to PDF and write to disk
    """
    fpath = p.get('outputdir', './output/')
    # Get number of cores to use
    multiproc = p.get('multiproc', 2)
    # Function to remove characters from nesting names that cannot be
    # used for filenames
    sanitize = p['sanitize']
    executor = setup.executor
    write_reports_for_nesting(unit_reports, 'unit', fpath, sanitize,
                              multiproc, Executor=executor)

@pipe
def write_onderdeel_reports(setup, onderdeel_reports, **p):
    """
    Generate functie reports to PDF and write to disk
    """
    fpath = p.get('outputdir', './output/')
    # Get number of cores to use
    multiproc = p.get('multiproc', 2)
    # Function to remove characters from nesting names that cannot be
    # used for filenames
    sanitize = p['sanitize']
    executor = setup.executor
    write_reports_for_nesting(onderdeel_reports, 'onderdeel', fpath, sanitize,
                              multiproc, Executor=executor)


@pipe
def write_org_report(org_report, **p):
    """
    Generate org report to PDF and write to disk
    """
    fpath = p.get('outputdir', './output/')

    fname = make_org_report_fname('organisatie')
    fullfname = fpath + fname + '.pdf'
    print(f"  Making PDF for {fname}", end="\r")
    html = HTML(string=org_report.html, base_url="")
    html.write_pdf(fullfname)

    print()
    print(f"  PDFs for 'organisatie' in: {fpath}")
    print("")
