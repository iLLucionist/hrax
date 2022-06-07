# The directory where output will be written to.
outputdir = '/my/output/dir'

# Configuration for making the reports
reports = dict(
    # The directory to write files to
    outputdir=outputdir,
    # The directory that contains the html templates for pages and elements
    tpldir='./assets/templates/',
    # The logfile for weasyprint, which makes the pdf files
    weasylog='./weasyprint.log',
    # Only reports are written for teams that equal or exceed this size
    min_team_size=5,
    # Only reports are written for functies that equal or exceed this size
    min_functie_size=5,
    # Only reports are written for units that equal or exceed this size
    min_unit_size=5,
    min_onderdeel_size=5,
    # The number of processor cores to uses for parallel execution.
    # Set this to the number of LOGICAL cores in the system.
    multiproc=16,
    # Whether results of a previous comparison year should be displayed
    # in the reports.
    prev=True,
    # When the difference is larger than 0.5 absolute points, mark it
    # as meaningfully different
    prev_mark=False,
    prev_mark_delta=0.5
)

analysis = dict(
    # The directory where data is stored to be read
    datapath="/where/the/input/data/is",
    # The file with employee data (must be CSV!)
    hrfile="hrfile.csv",
    # The file with the survey responses from qualtrics (must be CSV!)
    svfile="svfile.csv",
    # The file with the research model (must be CSV!)
    rmfile="rmfile.csv",
    # The file with the clustered multivariate regressions (must be CSV!)
    modfile="modfile.csv",

    # The column names in hr data and survey data that are used to link
    # te two together.
    merge_on_hr='mail',
    merge_on_sv='RecipientEmail',


    # The nestings for which aggregated results will be computed.
    # These should be the names of columns in either the hr data or sv data.
    # nestings=('team', 'functie', 'unit'),
    nestings=('team', 'functie', 'onderdeel'),
    # nestings=('team', 'functie'),

    # The minimum size that a nesting (e.g., team) should be.
    # TODO: This NOT used in the analysis. Instead, data is computed for
    # ALL nestings, regardless of size. In the reports, however, only
    # reports are generated that DO meet minimum nesting size.
    minnestingsize=5,

    # The variable name and value that indicates respondents have completed
    # the survey.
    finished_column='Finished',
    finished_value=1,

    # The variable name and value that indicates respondents have given
    # their consent to fill in the survey.
    consent_column='Consent',
    consent_value=1,

    # The upper/lower percentile to use for the R10 benchmark.
    # NOTE: If you want the upper/lower 10%, use .90.
    # NOTE: If you want the upper/lower 20%, use .80, etc.
    r10_quantile=.90,

    # Specify r10 comparison standard for nesting variable.
    # NOTE: format is r10_{nesting_name}_comparison='{comparison_name}'
    # Fill in the blanks. Should correspond to the values in 'nesting'
    # above in this configuration.
    r10_functie_comparison='team',
    r10_org_comparison='team',
    r10_onderdeel_comparison='team',

    # The significance value for regression weights.
    # NOTE: .1 is used to be a bit more lenient in practice.
    models_p_value=0.1,

    # Which statistic from the regression models to use to weigh growth
    # potentials. The default is 'mean_est', which means that it uses the
    # the absolute (without positive/negative sign) average regression
    # weight of an independent variable on all dependent variables.
    # Possible values are: 'mean_rank', 'max_est', 'mean_est'.
    # See models.model_iv_stats() for reference.
    weigh_growth_by='mean_est',

    # To compute and advice, weighted growth potentials are weighted
    # and ranked based on their relative contribution. This can be seen as
    # the 'explained variance' of every variable. This cutoff indicates
    # how much of the total explained variance of these weighted growth
    # potentials are allowed to base the advice on. Thus, if set to 0.7,
    # there will be as many weighted growth potentials available that
    # in total add up to a cumulative relative contribution of 70%.
    # This is caluclated in models.weighted_growth, and can be retrieved
    # via the results models.by_model.cutoff.<nesting>
    cumulative_growth_cutoff=0.7,

    # Standardized growth potentials are categorized in how much growth
    # potential there is to simply how much growth there is. These values
    # indicate the standard deviations of growth potential to assign each
    # growth potential a star. Thus, if a growth potential is
    # 'two_stars_sd' standard deviations above the mean (which is 0 because
    # z-distribution), it will be assigned two stars.
    one_star_sd=1,
    two_stars_sd=2,
    three_stars_sd=3,

    # Categorize scores.
    # NOTE: the right value is included, so in case of (1, 5), there will
    # be a category that does not include scores of 1 but does scores of 5.
    score_categories=(1, 5, 7, 10),
    score_category_names=('low', 'neutral', 'high'),

    # The number of advice entries to display.
    advice_n=3,

    # The number of summary entries to display.
    summary_ivs_high_n=4,
    summary_ivs_low_n=4,
    summary_dvs_high_n=3,
    summary_dvs_low_n=3,

    # Names of data files that contain scores of previous years.
    # When provided, these will be loaded and processed by the prev module.
    # NOTE: format: prev_aggregate_<nesting>
    # Nesting should correspond to the 'nestings' variable.
    # Organization level previous scores can be loaded by specifiying
    # 'prev_aggregate_org'.
    prev_aggregate_org='prev_agg_org.csv',
    prev_aggregate_team='prev_agg_team.csv',
    prev_aggregate_functie='prev_agg_functie.csv'
)
