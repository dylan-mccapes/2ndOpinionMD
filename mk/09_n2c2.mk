# =========================
# 9) n2c2 / i2b2 corpora
# =========================
n2c2-schema:
	@$(PSQL) -f database/schemas/text_n2c2_track3.sql

n2c2-t3-sample-schema: n2c2-schema
	@true

n2c2-t3-sample-import:
	@$(PY) server/scripts/ingest_n2c2_t3_sample.py --base data/n2c2/track3-sample

n2c2-t3-sample-qa:
	@$(PSQL) -c "SELECT COUNT(*) AS notes FROM text.n2c2_notes WHERE track='2022-T3';"
	@$(PSQL) -c "SELECT section_name, COUNT(*) FROM text.n2c2_ap_sections GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT label, COUNT(*) FROM text.n2c2_ap_relations GROUP BY 1 ORDER BY 2 DESC;"

n2c2-t3-sample-reset:
	@$(PSQL) -c "DELETE FROM text.n2c2_notes WHERE track='2022-T3' AND filename IN ('n2c2_sample_raw.csv','n2c2_sample.csv');"

n2c2-t3-backfill:
	@$(PSQL) -c "UPDATE text.n2c2_notes n SET note_text = m.text FROM text.mimic3_notes m WHERE n.track='2022-T3' AND n.external_id = m.row_id::text;"

n2c2-ap-extract-m3: n2c2-schema
	@$(PY) server/scripts/extract_ap_pairs_from_mimic.py --source m3 --limit $${LIMIT:-20000} --track MIII-AP

n2c2-ap-extract-miv: n2c2-schema
	@$(PY) server/scripts/extract_ap_pairs_from_mimic.py --source miv --domain discharge --limit $${LIMIT:-20000} --track MIV-AP

n2c2-ap-qa:
	@$(PSQL) -c "SELECT track, COUNT(*) AS notes FROM text.n2c2_notes GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT s.section_name, COUNT(*) FROM text.n2c2_ap_sections s GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT n.track, COUNT(*) AS rels FROM text.n2c2_ap_relations r JOIN text.n2c2_notes n USING (note_id) GROUP BY 1 ORDER BY 1;"

n2c2-export-gold:
	@$(PSQL) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='2022-T3') TO 'data/n2c2/train_gold.csv' CSV HEADER"

n2c2-export-silver-m3:
	@$(PSQL) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIII-AP') TO 'data/n2c2/train_silver_m3.csv' CSV HEADER"

n2c2-export-silver-miv:
	@$(PSQL) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIV-AP') TO 'data/n2c2/train_silver_miv.csv' CSV HEADER"

