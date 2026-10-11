"""OULAD teaching pipeline. Run from any directory with the lab Conda Python.

Stages are deliberately separate: download -> subset -> profile -> rdf -> query.
RDFS entailment is a small, separately reproducible demonstration.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import shutil
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw'
SUBSET = ROOT / 'data/interim'
OUT = ROOT / 'outputs'
SCHEMA = ROOT / 'ontology/education.rdfs.ttl'
GRAPH = ROOT / 'data/processed/oulad.ttl'
QUERIES = ROOT / 'queries'
TABLES = ['courses', 'assessments', 'studentInfo', 'studentRegistration',
          'studentAssessment', 'vle', 'studentVle']
OFFERING = ['code_module', 'code_presentation']
ENROLLMENT = OFFERING + ['id_student']
KEYS = {'courses': OFFERING, 'assessments': ['id_assessment'],
        'studentInfo': ENROLLMENT, 'studentRegistration': ENROLLMENT,
        'studentAssessment': ['id_student', 'id_assessment'],
        'vle': OFFERING + ['id_site'],
        'studentVle': ENROLLMENT + ['id_site', 'date']}
URL = 'https://archive.ics.uci.edu/static/public/349/open%2Buniversity%2Blearning%2Banalytics%2Bdataset.zip'


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def read_tables(folder, activity=False):
    import pandas as pd
    names = TABLES if activity else TABLES[:-1]
    # The UCI mirror encodes some missing values as '?'; the OU copy may use blanks.
    return {name: pd.read_csv(folder / f'{name}.csv', na_values=['?']) for name in names}


def download(args):
    """Extract only known filenames; never overwrite different raw data."""
    RAW.mkdir(parents=True, exist_ok=True)
    archive = RAW / 'oulad.zip'
    if not archive.exists():
        partial = RAW / 'oulad.zip.part'
        print('Downloading the UCI archive (~45 MB)...', flush=True)
        request = urllib.request.Request(URL, headers={'User-Agent': 'OULAD-teaching-project/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as target:
            shutil.copyfileobj(response, target)
        if not zipfile.is_zipfile(partial):
            raise ValueError('Download is not a ZIP archive; inspect the .part file.')
        partial.replace(archive)
    records = {}
    with zipfile.ZipFile(archive) as bundle:
        for table in TABLES:
            matches = [n for n in bundle.namelist() if Path(n).name == f'{table}.csv']
            if len(matches) != 1:
                raise ValueError(f'Expected exactly one {table}.csv in archive; got {matches}')
            target = RAW / f'{table}.csv'
            digest = hashlib.sha256()
            # Hash without keeping the large activity file in memory.
            with bundle.open(matches[0]) as source:
                if target.exists():
                    for chunk in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(chunk)
                    with target.open('rb') as existing_file:
                        existing = hashlib.file_digest(existing_file, 'sha256').hexdigest()
                    if existing != digest.hexdigest():
                        raise ValueError(f'{target} differs from the archive. Raw files were not overwritten.')
                else:
                    with target.open('wb') as dest:
                        for chunk in iter(lambda: source.read(1024 * 1024), b''):
                            digest.update(chunk)
                            dest.write(chunk)
            records[target.name] = {'bytes': target.stat().st_size, 'sha256': digest.hexdigest()}
            print(f'Ready: {target.name}', flush=True)
    save_json(RAW / 'manifest.json', {
        'source': URL, 'license': 'CC BY 4.0',
        'citation': 'Kuzilek, Hlosta, Zdrahal (2017), doi:10.1038/sdata.2017.171',
        'retrieved_or_verified_utc': datetime.now(timezone.utc).isoformat(), 'files': records,
        'note': 'Checksums record this download; they are not publisher-authenticated checksums.'})


def subset(args):
    import pandas as pd
    SUBSET.mkdir(parents=True, exist_ok=True)
    data = read_tables(RAW)
    selected = {}
    for name, frame in data.items():
        if name == 'studentAssessment':
            continue
        keep = frame.code_module.eq(args.module)
        if args.presentations:
            keep &= frame.code_presentation.isin(args.presentations)
        selected[name] = frame.loc[keep].copy()
    if selected['courses'].empty:
        raise ValueError('No course offerings match the requested selection.')
    if args.presentations and set(args.presentations) != set(selected['courses'].code_presentation):
        raise ValueError('At least one requested offering does not exist for this module.')
    selected['studentAssessment'] = data['studentAssessment'].loc[
        data['studentAssessment'].id_assessment.isin(selected['assessments'].id_assessment)].copy()
    # This is a relational subset, not independent head(N) calls on each table.
    for name, frame in selected.items():
        frame.to_csv(SUBSET / f'{name}.csv', index=False)
    if args.activity:
        path = SUBSET / 'studentVle.csv'
        first = True
        count = 0
        offerings = selected['courses'][OFFERING]
        for chunk in pd.read_csv(RAW / 'studentVle.csv', na_values=['?'], chunksize=200000):
            part = chunk.merge(offerings, on=OFFERING, how='inner', validate='many_to_one')
            part.to_csv(path, mode='w' if first else 'a', header=first, index=False)
            first = False
            count += len(part)
        print(f'studentVle: {count:,} rows selected')
    save_json(SUBSET / 'selection.json', {'module': args.module,
        'presentations': selected['courses'].code_presentation.tolist(),
        'include_activity': args.activity,
        'counts': {name: len(frame) for name, frame in selected.items()},
        'note': 'Original raw CSVs retained. No imputation or automatic row deletion.'})
    for name, frame in selected.items():
        print(f'{name}: {len(frame):,} rows')


def selected_activity():
    return json.loads((SUBSET / 'selection.json').read_text())['include_activity']


def quality_checks(data):
    import pandas as pd
    checks = []
    def add(rule, table, mask, severity='error', explanation=''):
        checks.append({'rule': rule, 'table': table, 'severity': severity,
                       'count': int(mask.sum()), 'explanation': explanation})
    def foreign(child, parent, columns, rule):
        frame = data[child]
        joined = frame[columns].merge(data[parent][columns].drop_duplicates(),
                                    on=columns, how='left', indicator=True)
        add(rule, child, joined['_merge'].eq('left_only'))
    for name, frame in data.items():
        add('required_key_components', name, frame[KEYS[name]].isna().any(axis=1))
        add('duplicate_key_rows', name, frame.duplicated(KEYS[name], keep=False))
    for child in ['assessments', 'studentInfo', 'studentRegistration', 'vle']:
        foreign(child, 'courses', OFFERING, 'offering_exists')
    foreign('studentRegistration', 'studentInfo', ENROLLMENT, 'registration_has_enrollment')
    foreign('studentInfo', 'studentRegistration', ENROLLMENT, 'enrollment_has_registration')
    foreign('studentAssessment', 'assessments', ['id_assessment'], 'assessment_exists')
    records = data['studentAssessment'].merge(data['assessments'][['id_assessment'] + OFFERING],
                                             on='id_assessment', how='left')
    joined = records.merge(data['studentInfo'][ENROLLMENT].drop_duplicates(), on=ENROLLMENT,
                           how='left', indicator=True)
    add('assessment_record_has_matching_enrollment', 'studentAssessment', joined['_merge'].eq('left_only'))
    sa = data['studentAssessment']
    add('score_in_0_100_when_present', 'studentAssessment', sa.score.notna() & ~sa.score.between(0, 100))
    add('missing_score_review', 'studentAssessment', sa.score.isna(), 'warning', 'Unknown is not zero.')
    add('banked_flag_is_0_or_1', 'studentAssessment', ~sa.is_banked.isin([0, 1]))
    add('submission_day_present', 'studentAssessment', sa.date_submitted.isna(), 'warning')
    a = data['assessments']
    add('assessment_type_vocabulary', 'assessments', ~a.assessment_type.isin(['TMA', 'CMA', 'Exam']))
    add('weight_in_0_100_when_present', 'assessments', a.weight.notna() & ~a.weight.between(0, 100))
    add('missing_deadline_review', 'assessments', a.date.isna(), 'warning', 'Do not invent an exact exam deadline.')
    si = data['studentInfo']
    add('final_result_vocabulary', 'studentInfo', ~si.final_result.isin(['Pass', 'Distinction', 'Fail', 'Withdrawn']))
    for name, columns in {'studentInfo': ['num_of_prev_attempts', 'studied_credits'],
                          'studentAssessment': ['date_submitted'], 'assessments': ['date'],
                          'studentRegistration': ['date_registration', 'date_unregistration']}.items():
        for column in columns:
            numeric = pd.to_numeric(data[name][column], errors='coerce')
            bad = data[name][column].notna() & (numeric.isna() | numeric.mod(1).ne(0))
            add(f'{column}_integer_when_present', name, bad)
    for column in ['num_of_prev_attempts', 'studied_credits']:
        add(f'{column}_nonnegative', 'studentInfo', si[column].notna() & (si[column].lt(0) | si[column].mod(1).ne(0)))
    length = data['courses']['module_presentation_length']
    add('offering_length_positive_integer', 'courses', length.isna() | length.le(0) | length.mod(1).ne(0))
    sr = data['studentRegistration']
    add('missing_registration_day_review', 'studentRegistration', sr.date_registration.isna(), 'warning',
        'Preserve unknown registration days; do not replace them with course start.')
    add('unregistration_before_registration_review', 'studentRegistration',
        sr.date_registration.notna() & sr.date_unregistration.notna() &
        sr.date_unregistration.lt(sr.date_registration), 'warning', 'Review rather than silently remove.')
    status = si.merge(sr, on=ENROLLMENT, how='left')
    add('withdrawal_status_date_disagreement', 'studentInfo',
        status.final_result.eq('Withdrawn').ne(status.date_unregistration.notna()), 'warning',
        'Review source completeness; missing is not a fabricated date.')
    vle = data['vle']
    add('resource_week_order_when_known', 'vle', vle.week_from.notna() & vle.week_to.notna() &
        vle.week_from.gt(vle.week_to), 'warning')
    if 'studentVle' in data:
        foreign('studentVle', 'studentInfo', ENROLLMENT, 'interaction_enrollment_exists')
        foreign('studentVle', 'vle', OFFERING + ['id_site'], 'interaction_resource_exists')
        clicks = data['studentVle'].sum_click
        add('click_count_nonnegative_integer', 'studentVle', clicks.isna() | clicks.lt(0) | clicks.mod(1).ne(0))
        days = data['studentVle']['date']
        add('interaction_day_integer', 'studentVle', days.isna() | days.mod(1).ne(0))
    return checks


def profile(args):
    import pandas as pd
    folder = RAW if args.raw else SUBSET
    # Full activity CSV is intentionally not loaded for a raw profile.
    data = read_tables(folder, activity=(not args.raw and selected_activity()))
    dest = OUT / 'profiling' / ('raw' if args.raw else 'subset')
    dest.mkdir(parents=True, exist_ok=True)
    chunks = ['<h1>OULAD data profile</h1>', '<p>Scope: ' + html.escape(str(folder)) + '</p>',
              '<p>Missing values remain unknown. Counts describe this extract, not causal conclusions.</p>']
    summary = {}
    for name, frame in data.items():
        stats = pd.DataFrame({'dtype': frame.dtypes.astype(str), 'missing': frame.isna().sum(),
                              'missing_pct': (frame.isna().mean()*100).round(2),
                              'distinct_nonmissing': frame.nunique()})
        stats.to_csv(dest / f'{name}_columns.csv')
        summary[name] = {'rows': len(frame), 'columns': len(frame.columns)}
        chunks += [f'<h2>{name}: {len(frame):,} rows</h2>', stats.to_html(),
                   '<h3>First five rows</h3>', frame.head().to_html(index=False),
                   '<h3>Numeric ranges (identifiers are not measurements)</h3>',
                   frame.describe().to_html()]
        for column in frame.columns:
            if frame[column].nunique() <= 20:
                frequencies = frame[column].value_counts(dropna=False).rename_axis(column).reset_index(name='rows')
                chunks += [f'<h3>Observed values: {html.escape(column)}</h3>', frequencies.to_html(index=False)]
        if args.ydata:
            from ydata_profiling import ProfileReport
            ProfileReport(frame, title=f'OULAD {name}', minimal=True).to_file(dest / f'{name}_ydata.html')
    checks = quality_checks(data)
    checks_df = pd.DataFrame(checks)
    checks_df.to_csv(dest / 'rule_checks.csv', index=False)
    failures = [row for row in checks if row['count']]
    chunks += ['<h2>Checks requiring attention</h2>',
               pd.DataFrame(failures).to_html(index=False) if failures else '<p>No flagged rows.</p>',
               '<h2>All checks</h2>', checks_df.to_html(index=False),
               '<p>Duplicate counts include all rows in duplicate groups. Warning counts are not error counts.</p>']
    if args.raw:
        chunks += ['<p>The large studentVle file is excluded here. Use subset --activity and profile to inspect selected activity.</p>']
    save_json(dest / 'summary.json', {'tables': summary, 'checks': checks})
    (dest / 'profile.html').write_text('<!doctype html><meta charset="utf-8"><title>OULAD profile</title>'
        '<style>body{font:16px system-ui;margin:40px;max-width:1300px}table{border-collapse:collapse;'
        'font-size:13px}th,td{border:1px solid #ddd;padding:6px}h2{margin-top:40px}</style>' +
        '\n'.join(chunks), encoding='utf-8')
    print(f'Profile: {dest / "profile.html"}')
    print(f'{len(failures)} checks flagged rows. Read rule_checks.csv before building RDF.')


def build_rdf(args):
    import pandas as pd
    from rdflib import Graph, Namespace, RDF, RDFS, Literal, XSD
    from urllib.parse import quote
    data = read_tables(SUBSET, selected_activity())
    checks = quality_checks(data)
    errors = [r for r in checks if r['severity'] == 'error' and r['count']]
    if errors:
        raise ValueError('Resolve source/schema errors before building RDF: ' + json.dumps(errors))
    ns = Namespace('https://example.org/oulad/schema#')
    base = 'https://example.org/oulad/id/'
    def iri(kind, *parts):
        from rdflib import URIRef
        return URIRef(base + kind + '/' + '/'.join(quote(str(p), safe='') for p in parts))
    def ident(value):
        return str(int(value))
    g = Graph()
    g.bind('edu', ns)
    g.bind('rdfs', RDFS)
    def literal(subject, predicate, value, datatype=None):
        if pd.notna(value):
            if datatype == XSD.integer:
                value = int(value)
            elif datatype == XSD.boolean:
                value = bool(value)
            g.add((subject, predicate, Literal(value, datatype=datatype)))
    def enrollment(row):
        return iri('enrollment', row.code_module, row.code_presentation, ident(row.id_student))
    for row in data['courses'].itertuples(index=False):
        module = iri('module', row.code_module)
        offering = iri('offering', row.code_module, row.code_presentation)
        g.add((module, RDF.type, ns.Module))
        literal(module, RDFS.label, row.code_module)
        g.add((offering, RDF.type, ns.CourseOffering))
        g.add((offering, ns.offeringOf, module))
        literal(offering, RDFS.label, f'{row.code_module} {row.code_presentation}')
        literal(offering, ns.presentationCode, row.code_presentation)
        literal(offering, ns.lengthDays, row.module_presentation_length, XSD.integer)
    for row in data['studentInfo'].itertuples(index=False):
        student = iri('student', ident(row.id_student))
        e = enrollment(row)
        g.add((student, RDF.type, ns.Student))
        literal(student, ns.studentId, ident(row.id_student))
        g.add((e, RDF.type, ns.Enrollment))
        g.add((e, ns.hasStudent, student))
        g.add((e, ns.inOffering, iri('offering', row.code_module, row.code_presentation)))
        literal(e, ns.finalResult, row.final_result)
        literal(e, ns.previousAttempts, row.num_of_prev_attempts, XSD.integer)
        # Context-dependent attributes stay on the enrollment, not timeless Student facts.
        for source, property_name in [('age_band', 'ageBand'), ('region', 'region'),
                                       ('highest_education', 'highestEducation')]:
            literal(e, ns[property_name], getattr(row, source))
    for row in data['studentRegistration'].itertuples(index=False):
        literal(enrollment(row), ns.registrationDay, row.date_registration, XSD.integer)
        literal(enrollment(row), ns.unregistrationDay, row.date_unregistration, XSD.integer)
    kinds = {'TMA': ns.TutorMarkedAssessment, 'CMA': ns.ComputerMarkedAssessment, 'Exam': ns.Exam}
    for row in data['assessments'].itertuples(index=False):
        a = iri('assessment', ident(row.id_assessment))
        # Deliberately assert the specific type: RDFS can infer the general Assessment type.
        g.add((a, RDF.type, kinds[row.assessment_type]))
        g.add((a, ns.assessmentInOffering, iri('offering', row.code_module, row.code_presentation)))
        literal(a, ns.deadlineDay, row.date, XSD.integer)
        literal(a, ns.weightPercent, row.weight, XSD.decimal)
    records = data['studentAssessment'].merge(data['assessments'][['id_assessment'] + OFFERING],
                                             on='id_assessment', validate='many_to_one')
    for row in records.itertuples(index=False):
        record = iri('assessment-record', ident(row.id_student), ident(row.id_assessment))
        g.add((record, RDF.type, ns.AssessmentRecord))
        g.add((record, ns.recordForEnrollment, enrollment(row)))
        g.add((record, ns.forAssessment, iri('assessment', ident(row.id_assessment))))
        literal(record, ns.submissionDay, row.date_submitted, XSD.integer)
        literal(record, ns.isBanked, row.is_banked, XSD.boolean)
        literal(record, ns.score, row.score, XSD.decimal)
    for row in data['vle'].itertuples(index=False):
        resource = iri('resource', row.code_module, row.code_presentation, ident(row.id_site))
        g.add((resource, RDF.type, ns.LearningResource))
        g.add((resource, ns.resourceInOffering, iri('offering', row.code_module, row.code_presentation)))
        literal(resource, ns.activityType, row.activity_type)
    if 'studentVle' in data:
        for row in data['studentVle'].itertuples(index=False):
            activity = iri('interaction', row.code_module, row.code_presentation,
                           ident(row.id_student), ident(row.id_site), ident(row.date))
            g.add((activity, RDF.type, ns.DailyInteraction))
            g.add((activity, ns.interactionForEnrollment, enrollment(row)))
            g.add((activity, ns.withResource, iri('resource', row.code_module, row.code_presentation, ident(row.id_site))))
            literal(activity, ns.interactionDay, row.date, XSD.integer)
            literal(activity, ns.clickCount, row.sum_click, XSD.integer)
    dest = ROOT / 'data/processed'
    dest.mkdir(parents=True, exist_ok=True)
    g.serialize(dest / 'oulad.ttl', format='turtle')
    save_json(dest / 'graph_summary.json', {'triples': len(g), 'selection': json.loads((SUBSET/'selection.json').read_text()),
                                          'schema_included': False, 'warnings': [r for r in checks if r['severity']=='warning' and r['count']]})
    print(f'Wrote {len(g):,} asserted triples: {dest / "oulad.ttl"}')


def query(args):
    from rdflib import Graph
    import csv
    g = Graph().parse(GRAPH)
    g.parse(SCHEMA)
    dest = OUT / 'answers'
    dest.mkdir(parents=True, exist_ok=True)
    statuses = {}
    for path in sorted(QUERIES.glob('*.rq')):
        if path.stem == '07_early_activity' and not selected_activity():
            statuses[path.stem] = {'status': 'unavailable', 'reason': 'Daily activity was not loaded.'}
            # Remove only this generated answer if a previous activity-enabled run created it.
            (dest / (path.stem + '.csv')).unlink(missing_ok=True)
            print(f'{path.name}: unavailable (activity not loaded)')
            continue
        result = g.query(path.read_text(encoding='utf-8'))
        rows = list(result)
        with (dest / (path.stem + '.csv')).open('w', newline='', encoding='utf-8') as target:
            writer = csv.writer(target)
            writer.writerow(map(str, result.vars))
            writer.writerows(['' if value is None else str(value) for value in row] for row in rows)
        print(f'{path.name}: {len(rows)} answer rows')
        statuses[path.stem] = {'status': 'answered', 'rows': len(rows)}
    save_json(dest / 'status.json', statuses)


def rdfs_demo(args):
    from rdflib import Graph, Namespace, RDF, RDFS, URIRef
    from owlrl import DeductiveClosure, RDFS_Semantics
    ns = Namespace('https://example.org/oulad/schema#')
    full = Graph().parse(GRAPH)
    # A bounded real-data sample keeps the lesson quick even with activity enabled.
    assessments = sorted(set(full.subjects(ns.assessmentInOffering, None)), key=str)[:3]
    students = sorted(set(full.subjects(RDF.type, ns.Student)), key=str)[:2]
    if not assessments or not students:
        raise ValueError('The graph needs at least one assessment and one student.')
    g = Graph().parse(SCHEMA)
    for subject in assessments + students:
        for triple in full.triples((subject, None, None)):
            g.add(triple)
    before = set(g)
    DeductiveClosure(RDFS_Semantics).expand(g)
    assert all((a, RDF.type, ns.Assessment) in g for a in assessments)
    assert all((s, RDF.type, ns.Person) in g for s in students)
    dest = OUT / 'rdfs'
    dest.mkdir(parents=True, exist_ok=True)
    g.serialize(dest / 'sample_inferred.ttl', format='turtle')
    examples = ['# RDFS demonstration', '', 'This is a bounded sample, not the full inferred dataset.', '',
                f'Before: {len(before)} triples. After: {len(g)} triples.', '',
                'Specific assessment types entail Assessment; Student entails Person.', '']
    for subject in assessments:
        examples.append(f'- {subject} is inferred to be an Assessment.')
    # Isolate the bad assertion so it can never contaminate the project graph.
    bad = Graph().parse(SCHEMA)
    thing = URIRef('https://example.org/oulad/demo/not-a-real-enrollment')
    bad.add((thing, ns.hasStudent, students[0]))
    DeductiveClosure(RDFS_Semantics).expand(bad)
    assert (thing, RDF.type, ns.Enrollment) in bad
    examples += ['', 'Domain demonstration: asserting demo:not-a-real-enrollment hasStudent a student',
                 'infers that the subject is an Enrollment. RDFS raises no validation error.',
                 'Range similarly infers the type of the object; it does not check a dropdown list.',
                 'Required fields, uniqueness, score ranges, and cross-record consistency need explicit checks/SHACL.']
    (dest / 'explanation.md').write_text('\n'.join(examples), encoding='utf-8')
    print(f'RDFS demonstration passed: {dest / "explanation.md"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('download')
    sub = commands.add_parser('subset')
    sub.add_argument('--module', default='AAA')
    sub.add_argument('--presentations', nargs='+')
    sub.add_argument('--activity', action='store_true')
    pro = commands.add_parser('profile')
    pro.add_argument('--raw', action='store_true')
    pro.add_argument('--ydata', action='store_true', help='Also generate lab-style ydata reports (slower).')
    commands.add_parser('rdf')
    commands.add_parser('query')
    commands.add_parser('rdfs')
    args = parser.parse_args()
    {'download': download, 'subset': subset, 'profile': profile,
     'rdf': build_rdf, 'query': query, 'rdfs': rdfs_demo}[args.command](args)


if __name__ == '__main__':
    main()
