# HR ANALYTICS (hrax)

This repository contains a HR analytics (hrax) pipeline.

This software reads multiple input files, puts them through a data pipeline
and produces multiple results files.

## THE PIPELINE

### CONFIGURATION

The behavior of the data pipeline can be configured in `config.py`. See
additional details there.

### INPUT FILES

There are at least four input files, and a fifth optional one (see
`config.py`):
1. `rmfile` is the research model csv file that describes every measured
   construct and must correspond to items (column names) in the next file. This
   file also contains options and switches as to how the constructs should be
   treated (e.g., should the be included in the report, should they be
   reversed, etc.)
2. `svfile` is the survey csv file that contains raw scores for participants
   that took the survey, such as a downloaded Qualtrics dataset.
3. `hrfile` contains employee records (such as age, team name, etc). This file
   is typically delivered by customer companies.
4. `modfile` contains the regression models that are run to be used to
   calculate additional statistics (see `models.py`).
5. The optional fifth file is actually a collection of files that can be used
   to calculate and compare scores of previous years with the current year. For
   every nesting or aggregate level (e.g., organisation-level, team-level, job
   type-level) a csv file corresponding to the nesting name can be specified
   (see `config.py`). The data pipeline then automatically calculates comparison
   scores between the current data and this previous data (see `prev.py`).

### PROCESSING

The pipeline is split up in roughly two parts:
1. Analysis (see `analysis.py`)
2. Reports (see `reports.py`) 

Calculating analytic results can be obtained by running the `results` pipe (see
`run.py`). The entire pipeline can be executed from the terminal using `python3
run.py <ARGS>` (see `args.py`).

Helper functions that are used throughout can be found in `helpers.py`. More
domain-specific helper functions are put in each respective module (see below).

The **analysis**-part roughly consists of the following collections of
operations:
1. `prepare_data.py` loads the input files, and transforms them so they can be
   used in the pipeline. Here is where scales are constructed, and means and
   nesting (aggregated) scores are calculated.
2. `benchmark.py` calculates the r10 benchmark and growth potential scores (see
   `growhp` on github page of iLLucionist).
3. `models.py` is where statistical models (e.g., regression) are calculated
   and relevant statistics are extracted and transformed into useful data
   structures (e.g., tables).
4. `rankings.py` is where benchmark scores and regression models are integrated
   to calculate ranked scores that are then used to generate advice that is
   later used in reports.
5. `prev.py` is where current scores are compared to configured earlier scores
   for nesting levels (see also `config.py`)
6. `entities.py` is where all the analytic results of the preceding steps are
   transformed into easy to understand data structures that the report part
   uses to generate html and pdf reports.
7. (OPTIONAL) if set (`params.dodump`), an additional excel file will be
   generated with the output of each step in the pipeline in separate sheets.
8. (OPTIONA) if set (`params.dodataset`), an additional dataset is generated
   that includes automatically generated scales and aggregated means.

The **results**-part takes the analytic results from `results()` (see `run.py`)
and uses that to generate html and pdf reports. Currently, reports can be
generated for these nesting levels: org, team, function (job profile), unit,
and onderdeel. These are arbitrary and specifically implemented to meet
customer's demands. The code can be easily adapted to add reports for
additional or different nesting levels, as long as there is a column in the
`hrfile` (see `config.py`) that corresponds to that nesting levels:
1. HTML files are generated for each report (example: `org_report`,
   `team_reports`
2. These html files are then rendered to pdf files using `weasyprint` (example:
   `write_org_report`, `write_team_reports`)
3. The pdf files are zipped to ease exchange of reports to clients.

## DEPENDENCIES

### INTERNAL DEPENDENCIES

There are two python libraries I wrote myself that are dependencies for this
data pipeline:
1. `nowslides` is a micro-framework (a kind of templating system and static
   site generator) that takes in a specification `yaml`-file and then renders a
   html file.
2. `nowpipes` is a micro-framework that enables the construction of data
   pipelines using decorator functions, and then automatically calculates the
   correct execution order, executes it, and stores the results in an
   data-optimized (e.g., mostly numpy data structures) dictionary.

### EXTERNAL DEPENDENCIES

This software has a couple python packages as dependencies
(see `pyproject.toml`).

## INSTALLATION

The easiest way to get this up and running is to use `poetry` to make a
self-contained python environment, and install the according dependencies.
From within this environment, everything can be run.

**IMPORTANT**: there are two extra dependencies (see this github page) that I
have also developed as supporting frameworks to structure the data pipeline
and to separate responsibilities:

- `nowslides`, which takes the resulting data structures and generates
  HTML/CSS
- `nowpipes`, which is a micro-framework that uses a decorator function to
  compose data pipelines, and that automatically determines the right order
  of execution.

Finally, the front-end design (HTML/CSS) template files are in `assets/`.

## CONFIGURATION

All configuration resides in `config.py`, see documentation for options there.

Most importantly, the `outputdir` var at the top is where output files will
be stored (HTML files and ZIP files).

The `datapath` var in the `analysis`-dict is where the input directory should
be specified, which are all the files the software might read.

There are essentially FOUR files that are used as input:

- `hrfile` is the file with employee data (name, function, team, etc)
- `svfile` is the file with the raw scores on questions
- `rmfile` is the file with the research mode, which contains names and
  descriptions of constructs
- `modfile` is the file that specifies which regression models are run

Optionally, comparison scores can be specified (see end of `config.py`) for
each aggregation level.

## SPECIFICATION OF REPORT CONTENT

`nowreports` processes `yaml`-based spec files.

## EXECUTION

The execution flow is straightforward, and there is a separation into two
broad responsibilities:

1. The `analysis`-module calculates results, generates a dump excel-sheet
(`output_files`) and a transformed dataset that has results added as columns
to the input survey file (see `svfile` in `config.py`).

2. The `reports`-module uses these results to make HTML reports, then PDFs,
then ZIP-files.

This software can be used in two ways:

1. Use `runint.py` to calculate results, and use `ipython` or `python3 -I` to
   drop into an interactive shell. You can now use the `results`-object and
   use pandas queries to inspect the results. Reports will not be generated.

2. Use `run.py` to also make reports. You can use this as a python-based
   commandline tool (e.g. `python3 run.py <OPTS AND ARGS>`). Look at
   `run.py` for commandline parameters and toggles.
