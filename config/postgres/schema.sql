-- Applied inside a transaction after setting the selected project schema.
CREATE TABLE IF NOT EXISTS courses (
 code_module text NOT NULL, code_presentation text NOT NULL,
 module_presentation_length integer NOT NULL CHECK (module_presentation_length>0),
 PRIMARY KEY(code_module,code_presentation));
CREATE TABLE IF NOT EXISTS student_info (
 code_module text NOT NULL, code_presentation text NOT NULL, id_student text NOT NULL,
 gender text, region text, highest_education text, imd_band text, age_band text,
 num_of_prev_attempts integer NOT NULL CHECK(num_of_prev_attempts>=0), studied_credits integer,
 disability text, final_result text NOT NULL CHECK(final_result IN ('Pass','Distinction','Fail','Withdrawn')),
 PRIMARY KEY(code_module,code_presentation,id_student),
 FOREIGN KEY(code_module,code_presentation) REFERENCES courses);
CREATE TABLE IF NOT EXISTS student_registration (
 code_module text NOT NULL, code_presentation text NOT NULL, id_student text NOT NULL,
 date_registration integer, date_unregistration integer,
 PRIMARY KEY(code_module,code_presentation,id_student),
 FOREIGN KEY(code_module,code_presentation,id_student) REFERENCES student_info);
CREATE TABLE IF NOT EXISTS assessments (
 code_module text NOT NULL, code_presentation text NOT NULL, id_assessment text PRIMARY KEY,
 assessment_type text NOT NULL CHECK(assessment_type IN ('TMA','CMA','Exam')),
 deadline_day integer, weight numeric NOT NULL CHECK(weight BETWEEN 0 AND 100),
 FOREIGN KEY(code_module,code_presentation) REFERENCES courses);
CREATE TABLE IF NOT EXISTS student_assessment (
 id_assessment text NOT NULL REFERENCES assessments, id_student text NOT NULL,
 date_submitted integer, is_banked boolean NOT NULL, score numeric CHECK(score BETWEEN 0 AND 100),
 PRIMARY KEY(id_assessment,id_student));
CREATE TABLE IF NOT EXISTS vle (
 id_site text NOT NULL, code_module text NOT NULL, code_presentation text NOT NULL,
 activity_type text NOT NULL, week_from integer, week_to integer,
 PRIMARY KEY(code_module,code_presentation,id_site),
 FOREIGN KEY(code_module,code_presentation) REFERENCES courses);
CREATE OR REPLACE VIEW v_modules AS SELECT DISTINCT code_module FROM courses;
CREATE OR REPLACE VIEW v_offerings AS SELECT *, code_module || ' ' || code_presentation AS label FROM courses;
CREATE OR REPLACE VIEW v_students AS SELECT DISTINCT id_student FROM student_info;
CREATE OR REPLACE VIEW v_enrollments AS SELECT i.*, r.date_registration, r.date_unregistration
 FROM student_info i LEFT JOIN student_registration r USING(code_module,code_presentation,id_student);
CREATE OR REPLACE VIEW v_assessments AS SELECT * FROM assessments;
CREATE OR REPLACE VIEW v_assessment_records AS SELECT s.*,a.code_module,a.code_presentation
 FROM student_assessment s JOIN assessments a USING(id_assessment);
CREATE OR REPLACE VIEW v_resources AS SELECT * FROM vle;
