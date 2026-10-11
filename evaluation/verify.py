"""Reconcile RDF answers against CSVs using an independent SQLite query layer."""
from pathlib import Path
import json
import sqlite3
import sys
import pandas as pd
from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/common'))
import pipeline


def main():
    data = pipeline.read_tables(pipeline.SUBSET, pipeline.selected_activity())
    connection = sqlite3.connect(':memory:')
    for name, frame in data.items():
        frame.to_sql(name, connection, index=False)
    g = Graph().parse(pipeline.GRAPH)
    g.parse(pipeline.SCHEMA)
    ns = Namespace('https://example.org/oulad/schema#')
    checks = []
    def check(name, actual, expected):
        if actual != expected:
            raise AssertionError(f'{name}: actual={actual}, expected={expected}')
        checks.append({'check': name, 'status': 'passed'})
        print(f'PASS: {name}')
    counts = {
        ns.Student: data['studentInfo'].id_student.nunique(),
        ns.Enrollment: len(data['studentInfo']), ns.CourseOffering: len(data['courses']),
        ns.AssessmentRecord: len(data['studentAssessment']), ns.LearningResource: len(data['vle'])}
    for kind, count in counts.items():
        check(str(kind).split('#')[-1] + ' node count', len(set(g.subjects(RDF.type, kind))), count)
    def answer(name):
        return list(g.query((pipeline.QUERIES / name).read_text()))
    query1 = answer('01_enrollments.rq')
    check('enrollment counts by offering',
          sorted((str(r.offering).split('/')[-1], int(r.enrollments)) for r in query1),
          sorted((str(p), len(part)) for p, part in data['studentInfo'].groupby('code_presentation')))
    check('all assessment subtypes included', len(answer('02_assessments.rq')), len(data['assessments']))
    sql_late = connection.execute('''SELECT s.id_student, s.id_assessment, s.date_submitted-a.date
      FROM studentAssessment s JOIN assessments a USING(id_assessment)
      WHERE s.is_banked=0 AND s.date_submitted>a.date''').fetchall()
    actual_late = {(int(str(r.enrollment).split('/')[-1]), int(str(r.assessment).split('/')[-1]),
                    int(r.daysLate)) for r in answer('03_late_records.rq')}
    check('late record identities and days (SQL vs SPARQL)', actual_late,
          {(int(s), int(a), int(d)) for s, a, d in sql_late})
    low = connection.execute('SELECT COUNT(*) FROM studentAssessment WHERE score<40').fetchone()[0]
    check('low scores', len(answer('04_low_scores.rq')), low)
    unknown = connection.execute('SELECT COUNT(*) FROM studentAssessment WHERE score IS NULL').fetchone()[0]
    check('unknown scores retained as records', len(answer('06_unknown_scores.rq')), unknown)
    outcomes = connection.execute('SELECT code_presentation, final_result, COUNT(*) FROM studentInfo GROUP BY 1,2').fetchall()
    actual = {(str(r[0]).split('/')[-1], str(r[1]), int(r[2])) for r in answer('05_outcomes.rq')}
    check('outcomes by offering', actual, set(outcomes))
    if pipeline.selected_activity():
        sql = connection.execute('''SELECT code_module,code_presentation,id_student,SUM(sum_click),COUNT(DISTINCT id_site)
                                   FROM studentVle WHERE date>=0 AND date<28 GROUP BY 1,2,3''').fetchall()
        expected = {(f'{m}/{p}/{s}', int(clicks), int(resources)) for m,p,s,clicks,resources in sql}
        actual = {('/'.join(str(r.enrollment).split('/')[-3:]),int(r.clickCount),int(r.resourceCount))
                  for r in answer('07_early_activity.rq')}
        check('early activity aggregates', actual, expected)
    check('no invented nan literals', any(str(o).lower() == 'nan' for s,p,o in g), False)
    # Boundary cases for the late definition, independent of the real-data distribution.
    boundary = Graph()
    from rdflib import URIRef, Literal, XSD
    a = URIRef('urn:test:assessment')
    boundary.add((a, ns.deadlineDay, Literal(10, datatype=XSD.integer)))
    for name, day, banked in [('same_day',10,False), ('late',11,False), ('banked',11,True)]:
        record = URIRef('urn:test:' + name)
        boundary.add((record,ns.forAssessment,a))
        boundary.add((record,ns.recordForEnrollment,URIRef('urn:enrollment:' + name)))
        boundary.add((record,ns.submissionDay,Literal(day,datatype=XSD.integer)))
        boundary.add((record,ns.isBanked,Literal(banked)))
    result = list(boundary.query((pipeline.QUERIES/'03_late_records.rq').read_text()))
    check('same-day and banked boundary cases', [str(r.enrollment) for r in result], ['urn:enrollment:late'])
    pipeline.rdfs_demo(None)
    checks.append({'check': 'RDFS subclass/domain demonstration', 'status': 'passed'})
    pipeline.save_json(ROOT / 'outputs/verification.json', checks)
    print(f'{len(checks)} verification checks passed.')


if __name__ == '__main__':
    main()
