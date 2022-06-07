from nowslides import get_template
from entities import get_score, get_ivstat, get_prev
from helpers import df_to_list, score_percentage_multiply
from numpy import isnan

from sys import exit


def team_top4(e, v, p):
    return('<div>TEAM TOP4</div>')


def listing(e, v, p):
    html = '<ul class="list">'

    for li in e['contents']:
        html += '<li><span class="number">' + str(li['number']) + '</span>'
        html += '<span class="title">' + str(li['title']) + '</span>'
        html += '<span class="explanation">' + str(li['explanation']) + '</span></li>\n'

    html += "</ul>"

    return html


def score(e, v, p):
    tpl = get_template('score')
    score = get_score(v['scores'], e['var'])
    # No score available (slight hack, see score_percentage_multiply)
    if score['current_score_per_width'] == 0:
        score['current_score'] = "-"
    else:
        score['current_score'] = round(score['current_score'], 1)

    if e.get('prev', False):
        prev_score = get_prev(v['prev'], e['var'])
        prev_mark = v.get('prev_mark', False)
        prev_mark_delta = v.get('prev_mark_delta', 0.5)
        if prev_score is not None:
            score['prev_score'] = prev_score
            score['prev_score_per'] = score_percentage_multiply(prev_score, 10,
                                                                True)
            if prev_mark is True and score['current_score'] != '-':
                actual_delta = score['current_score'] - score['prev_score']
                # Do not show prev mark until difference large enough
                score['prev_mark'] = False
                if actual_delta < 0 and abs(actual_delta) >= prev_mark_delta:
                    score['prev_mark'] = True
                    score['prev_mark_text'] = "&darr;"
                elif actual_delta > 0 and abs(actual_delta) >= prev_mark_delta:
                    score['prev_mark'] = True
                    score['prev_mark_text'] = "&uarr;"
        else:
            score['prev_score'] = None

    return tpl.render(**score)


def ivstat(e, v, p):
    tpl = get_template('bar')
    score = get_ivstat(v['ivstats'], e['var'], e['dvcluster'], e['ivcluster'])
    score['current_score'] = round(score['rel_est'], 1)
    score['mean_est'] = round(score['mean_est'], 2)
    score['showb'] = p.get('showb', True)
    return tpl.render(**score)


def summary(e, v, p):
    if e['type'] == 'dvs' and e['hilo'] == 'high':
        score = v['high_dvs']
    elif e['type'] == 'dvs' and e['hilo'] == 'low':
        score = v['low_dvs']
    elif e['type'] == 'ivs' and e['hilo'] == 'high':
        score = v['high_ivs']
    elif e['type'] == 'ivs' and e['hilo'] == 'low':
        score = v['low_ivs']

    rename = {'name': 'title', 'definition': 'explanation'}
    keep = ['number', 'title', 'explanation']
    score = df_to_list(score, rename=rename, keep=keep)
    html = listing({'contents': score}, v, p)
    return html


def advice(e, v, p):
    if isinstance(e, dict) and e.get('dvcluster') is not None:
        score = v['advice_by_dvcluster'][e['dvcluster']]
    else:
        score = v['advice']
    rename = {'name': 'title', 'definition': 'explanation'}
    keep = ['number', 'title', 'explanation', 'postfix']

    def make_postfix(row):
        postfix = ''
        if 'majority' in row:
            if int(row['majority']) == 1:
                postfix = 'verhoogt'
            elif int(row['majority']) == -1:
                postfix = 'vermindert'
            else:
                if row['direction'] == 'positive':
                    postfix = 'verhoogt'
                else:
                    postfix = 'vermindert'
        return ' (' + postfix + ')'

    # Add postfix for sign to title of advice entry
    postfix = score.apply(lambda x: make_postfix(x), axis='columns')
    score['postfix'] = postfix
    score['name'] = score['name'] + score['postfix']
    score = df_to_list(score, rename=rename, keep=keep)
    html = listing({'contents': score}, v, p)
    return html


def numberbox(e, v, p):
    tpl = get_template('number')
    return tpl.render(**e)


elparsers = [
    team_top4,
    listing,
    score,
    summary,
    advice,
    numberbox,
    ivstat
]
