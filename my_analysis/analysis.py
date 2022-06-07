from importlib import reload

import pandas as pd

from nowpipes import Pipeline, pipe

from helpers import (delete_file_if_exists, make_org_report_fname,
                     make_correlation_table, top_effects_table)

import config


@pipe
def results(**p):
    """
    Compute results.
    """
    import helpers
    import prepare_data
    import benchmark
    import models
    import rankings
    import prev
    import entities

    reload(helpers)
    reload(prepare_data)
    reload(benchmark)
    reload(models)
    reload(rankings)
    reload(prev)
    reload(entities)

    # Make pipeline
    analysis = Pipeline()
    analysis_config = config.analysis
    analysis.config(**analysis_config)

    # Add analysis parts and run analysis
    analysis.add(prepare_data, benchmark, models, rankings,
                 prev, entities)
    analysis.run(verbose=True, indent=1)

    return analysis


@pipe
def output_files(results, **p):
    """
    Make a data dump to excel.
    """
    # TODO: account for different nestings enabled/disabled
    fname = p['outputdir'] + make_org_report_fname('_dump') + '.xlsx'
    delete_file_if_exists(fname)

    writer = pd.ExcelWriter(fname)

    r = results

    r.nesting.team.to_excel(writer, sheet_name='team_names')
    r.data.hr.to_excel(writer, sheet_name='hrdata')
    r.aggregate.org.to_excel(writer, sheet_name='mean_org')
    r.aggregate.team.to_excel(writer, sheet_name='mean_team')
    r.r10.org.to_excel(writer, sheet_name='r10_org')
    r.r10.team.to_excel(writer, sheet_name='r10_team')
    r.growth.team.to_excel(writer, sheet_name='growth_team')
    r.growth_descriptives.team.to_excel(writer, sheet_name='gdesc_team')
    r.excellent.team.to_excel(writer, sheet_name='excel_team')
    r.data.rm.to_excel(writer, sheet_name='rmmodel')
    r.models.all.ivstats.to_excel(writer, sheet_name='allmodels')
    r.prev.org.to_excel(writer, sheet_name='prev_org')
    r.prev.team.to_excel(writer, sheet_name='prev_team')
    r.prev.functie.to_excel(writer, sheet_name='prev_func')

    # r.nesting.unit.to_excel(writer, sheet_name='unit_names')
    # r.aggregate.unit.to_excel(writer, sheet_name='mean_unit')
    # r.r10.unit.to_excel(writer, sheet_name='r10_unit')

    r.nesting.onderdeel.to_excel(writer, sheet_name='onderdeel_names')
    r.aggregate.onderdeel.to_excel(writer, sheet_name='mean_onderdeel')
    r.r10.onderdeel.to_excel(writer, sheet_name='r10_onderdeel')

    signs_df = pd.concat(r.signs.by_dvcluster)
    signs_df.to_excel(writer, sheet_name='signs')

    df = r.data.use[r.research_model.grade_name]
    names = r.glossary[['name']]
    corrs = make_correlation_table(df, names)
    corrs.to_excel(writer, sheet_name='correlations')

    topeffects = top_effects_table(r)
    topeffects.to_excel(writer, sheet_name='top_effects')

    for modname in r.models.all.table['model'].unique():
        r.models[modname].table.to_excel(writer, modname)

    writer.save()


@pipe
def output_dataset(results, **p):
    """
    Generate the questionnaire dataset with all additional computed results
    from the analyses (scale means, grade scores, etc.).
    """
    fname = p['outputdir'] + make_org_report_fname('_dataset') + '.xlsx'
    delete_file_if_exists(fname)
    dataset = results.data.all
    dataset.to_excel(fname)
