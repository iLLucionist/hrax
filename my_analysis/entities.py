# from nowpipes import pipe

# from copy import deepcopy
from pandas import DataFrame

from helpers import (score_percentage_multiply,
                     scale_iv_var_names, scale_dv_var_names)

from prev import has_prev, has_prev_for_nesting_no

from sys import exit
from nowpipes import Pipeline, pipe
from copy import deepcopy


def ranked_advice(wg, signs, n=5, dvclus=None):
    """
    Get the advice based on weighted growth. This function will sort the
    weighted growth potentials from highest to lowest and will return top n

    Arguments:
    wg -- weighted growth potential table of nesting entry
    n -- number of weighted growth potentials to return (default: 5)
    """

    # Sort values
    wglist = DataFrame(wg.sort_values(axis=0, ascending=False))
    # Rename values column
    wglist = wglist.rename(columns={wglist.columns[0]: 'score'})
    # Add name of scores as column
    wglist['grade_name'] = wglist.index
    # Reorder columns
    # wglist = wglist[['grade_name', 'score']]
    # Reset index to numeric values
    wglist.reset_index(drop=True, inplace=True)
    # Only retain top n rows
    wglist = wglist.head(n=n)

    if dvclus is not None:
        signs = signs.by_dvcluster[dvclus]
        signs = signs[signs.grade_name.isin(wglist.grade_name)]
        signs = signs[['grade_name', 'majority', 'direction']]
        wglist = wglist.merge(signs, how='inner', left_on='grade_name', right_on='grade_name')

    return wglist


def response_stats(response):
    r = response.to_dict()
    r['respons'] = round(float(r['respons']))
    return(r)


def nesting_scores(agg, r10):
    # Rename value colum
    agg = DataFrame(agg)
    agg = agg.rename(columns={agg.columns[0]: 'current_score'})
    # Add columns
    agg['current_score_per_width'] = agg['current_score'].apply(
            score_percentage_multiply, args=(10.0, True))
    agg['grade_name'] = agg.index
    agg.reset_index(drop=True, inplace=True)

    # Combine scores with r10 values
    scores = agg.merge(r10, how='inner', left_on='grade_name',
                       right_on='grade_name')

    # Put grade_name column to beginning
    scores.insert(0, 'grade_name', scores.pop('grade_name'))

    return scores


def scores_r10_df(agg, r10):
    r10keep = ['low10_grade', 'high10_grade',
               'low10_grade_per', 'high10_grade_per',
               'grade_name', 'direction']
    r10s = r10[r10keep]
    r10s = deepcopy(r10s)
    r10s['high10_grade_per_right'] = 100 - r10s['high10_grade_per']
    return r10s


def sort_and_summarize(col, lown=3, highn=3):
    col = DataFrame(col)
    col = col.rename(columns={col.columns[0]: 'score'})
    col = col.sort_values(col.columns[0], ascending=False)
    col['grade_name'] = col.index
    col.reset_index(drop=True, inplace=True)

    res = {'low': col.tail(lown), 'high': col.head(highn)}

    return res


def get_advice(results, nesting, no):
    """
    Make an advice dict with all data required to render it to a report.
    """
    advice = results.advice[nesting][no]
    advice = advice.merge(results.glossary, how='inner', left_on='grade_name',
                          right_on='grade_name')
    return advice


def get_advice_by_dvcluster(results, nesting, no):
    """
    Make an advice dict with all data required to render it to a report.
    """
    dvclusters = results.advice.by_dvcluster.keys()
    advice = {}
    for dvclus in dvclusters:
        advice[dvclus] = results.advice.by_dvcluster[dvclus][nesting][no]
        advice[dvclus] = advice[dvclus].merge(results.glossary,
                                              how='inner',
                                              left_on='grade_name',
                                              right_on='grade_name')
    return advice


def get_org_advice_for_dvclusters(results):
    """
    Make an advice dict with all data required to render it to a report.
    """
    dvclusters = results.advice.org.by_dvcluster.keys()
    advice = {}
    for dvclus in dvclusters:
        advice[dvclus] = results.advice.org.by_dvcluster[dvclus]
        advice[dvclus] = advice[dvclus].merge(results.glossary,
                                              how='inner',
                                              left_on='grade_name',
                                              right_on='grade_name')
    return advice


def get_response(results, nesting, no):
    """
    Get response statistics for nesting.
    """
    resp = results.response[nesting][no]

    return resp


def get_scores(results, nesting, no):
    scores = results.scores[nesting][no]
    scores = scores.merge(results.glossary, how='inner',
                          left_on='grade_name', right_on='grade_name')
    return scores


def get_score(scores, varname):
    score = scores[scores['meanname'] == varname]
    score = score.reset_index().transpose().to_dict()[0]
    return score


def get_prev(prev, varname):
    if prev is None:
        return False
    score = None
    if varname in prev.columns:
        score = float(prev[varname])
    return score


def get_prev_scores(results, nesting, no):
    if has_prev(results, nesting) is False:
        return None
    prev = results.prev[nesting]
    if has_prev_for_nesting_no(prev, no) is False:
        return None
    return prev[prev.no == no]


def get_org_prev_scores(results):
    if has_prev(results, 'org') is False:
        return None
    return results.prev.org


def get_summary(results, nesting, no, typ, hilo='low'):
    summary = results.summary[nesting][typ][no][hilo]
    summary = summary.merge(results.glossary, how='inner',
                            left_on='grade_name', right_on='grade_name')
    return summary


def get_org_response(results, value="Organisatie", response=None):
    n = len(results.data.use)
    size = len(results.data.hr)
    if response is None:
        response = round((float(n) / size) * 100)

    return {
        'value': value,
        'n': n,
        'size': size,
        'respons': response
    }


def get_org_scores(results):
    scores = results.scores.org
    scores = scores.merge(results.glossary, how='inner',
                          left_on='grade_name', right_on='grade_name')
    return scores


def get_org_summary(results, typ, hilo='low'):
    summary = results.summary.org[typ][hilo]
    summary = summary.merge(results.glossary, how='inner',
                            left_on='grade_name', right_on='grade_name')
    return summary


def get_ivstat(ivstats, varname, dvcluster=None, ivcluster=None):
    df = ivstats
    df = df[df['dvcluster'] == dvcluster]
    df = df[df['ivcluster'] == ivcluster]
    score = df[df['meanname'] == varname]
    score = score.reset_index().transpose().to_dict()[0]
    return score


def get_ivstats(results):
    ivstats = results.models.all.ivstats
    ivstats['grade_name'] = ivstats.index
    ivstats = ivstats.merge(results.glossary, how='inner',
                            left_on='grade_name', right_on='grade_name')
    return ivstats


@pipe
def glossary(data, research_model, **p):
    """
    Make a glossary that contains the title and definition of all
    variables in the research model.
    """
    readables = data.rm[['name', 'definition', 'meanname']]
    names = research_model[['meanname', 'grade_name']]

    return readables.merge(names, how='inner', left_on='meanname',
                           right_on='meanname')


@pipe
def advice(glossary, models, weighted_growth, signs, **p):
    """
    Construct a list with the advice, which are the top strongest weighted
    growth potentials for an entry in a nesting.
    """
    dvclusters = weighted_growth.by_dvcluster.keys()
    r = {'by_dvcluster': {dvclus: {} for dvclus in dvclusters}}

    advice_n = p.get('advice_n', 5)

    # Org advice
    r['org'] = {'by_dvcluster': {dvclus: {} for dvclus in dvclusters}}
    for dvclus in dvclusters:
        org_dvclus = models.by_dvcluster[dvclus].head(advice_n)
        org_dvclus = org_dvclus[['iv', 'estabs']]
        org_dvclus = org_dvclus.rename(columns={'iv': 'grade_name',
                                                'estabs': 'score'})
        org_signs = signs.by_dvcluster[dvclus]
        org_signs = org_signs[org_signs.grade_name.isin(org_dvclus.grade_name)]
        org_signs = org_signs[['grade_name', 'majority', 'direction']]
        org_dvclus = org_dvclus.merge(org_signs, how='inner', left_on='grade_name', right_on='grade_name')
        r['org']['by_dvcluster'][dvclus] = org_dvclus

    for n in p['nestings']:
        advice = weighted_growth[n].apply(ranked_advice, axis='columns',
                                          args=(advice_n,))
        r[n] = advice

        # Advice per dvcluster
        for dvclus in dvclusters:
            wg_dvclus = weighted_growth['by_dvcluster'][dvclus][n]
            advice_dvclus = wg_dvclus.apply(ranked_advice, axis='columns',
                                            args=(signs, advice_n, dvclus))
            r['by_dvcluster'][dvclus][n] = advice_dvclus

    return r


@pipe
def response(nesting, **p):
    r = dict()

    for n in p['nestings']:
        resp = nesting[n].apply(response_stats, axis='columns')
        r[n] = resp

    return r


@pipe
def scores(nesting, r10, aggregate, research_model, **p):
    r = dict()

    # Only use grade names
    varnames = research_model['grade_name'].tolist()

    # Organization level
    agg = aggregate.org[varnames].transpose()

    cstd = p.get('r10_org_comparison', 'org')

    # r10s = scores_r10_df(agg, r10.org)
    r10s = scores_r10_df(agg, r10[cstd])
    r['org'] = nesting_scores(agg, r10s)

    for n in p['nestings']:
        agg = aggregate[n][varnames]
        cstd = p.get('r10_' + n + '_comparison', n)
        r10s = scores_r10_df(agg, r10[cstd])
        scor = agg.apply(nesting_scores, axis='columns', args=(r10s,))
        r[n] = scor

    return r


@pipe
def summary(nesting, aggregate, research_model, **p):
    ivs_low_n = p.get('summary_ivs_low_n', 3)
    ivs_high_n = p.get('summary_ivs_high_n', 3)
    dvs_low_n = p.get('summary_dvs_low_n', 3)
    dvs_high_n = p.get('summary_dvs_high_n', 3)

    r = {'org': {}}

    ivs = scale_iv_var_names(research_model)['grade_name']
    dvs = scale_dv_var_names(research_model)['grade_name']
    agg_ivs = aggregate.org[ivs].transpose()
    agg_dvs = aggregate.org[dvs].transpose()

    r['org']['ivs'] = sort_and_summarize(agg_ivs, ivs_low_n, ivs_high_n)
    r['org']['dvs'] = sort_and_summarize(agg_dvs, dvs_low_n, dvs_high_n)

    for n in p['nestings']:
        agg_ivs = aggregate[n][ivs]
        agg_dvs = aggregate[n][dvs]

        summ_ivs = agg_ivs.apply(sort_and_summarize, axis='columns', args=(
                                 ivs_low_n, ivs_high_n))
        summ_dvs = agg_dvs.apply(sort_and_summarize, axis='columns', args=(
                                 dvs_low_n, dvs_high_n))

        r[n] = {'ivs': summ_ivs, 'dvs': summ_dvs}

    return r
