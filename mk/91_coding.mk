API ?= http://127.0.0.1:8000
CURL ?= curl -fsS
NOTE ?= 62F with chest pain and dyspnea. ECG with ST depressions V4–V6. hs-Tn 220 ng/L. Dx: NSTEMI. DM2, HTN. ASA 325 mg, heparin, high-intensity statin; plan PCI.
SOURCES ?= icd10cm,icd11,rxnorm,loinc,chv,orphanet

coding-json:
	@jq -n --arg note "$(NOTE)" --arg sources "$(SOURCES)" '{note:$$note, sources:$$sources, limit:60}' | \
	$(CURL) -H 'Content-Type: application/json' -d @- \
	'$(API)/api/rag/coding?format=json&pretty=1' | jq -C . | sed '' # prints colored JSON w/o pager

coding-json-file:
	@jq -n --arg note "$(NOTE)" --arg sources "$(SOURCES)" '{note:$$note, sources:$$sources, limit:60}' | \
	$(CURL) -H 'Content-Type: application/json' -d @- \
	'$(API)/api/rag/coding?format=json&pretty=1' > coding.json && \
	echo "Wrote coding.json"

coding-csv:
	@jq -n --arg note "$(NOTE)" --arg sources "$(SOURCES)" '{note:$$note, sources:$$sources, limit:60}' | \
	$(CURL) -H 'Content-Type: application/json' -d @- \
	-o coding.csv '$(API)/api/rag/coding?format=csv' && \
	echo "Wrote coding.csv" && \
	( command -v column >/dev/null 2>&1 && cat coding.csv | column -s, -t | sed '' || true )

coding-pdf:
	@jq -n --arg note "$(NOTE)" --arg sources "$(SOURCES)" '{note:$$note, sources:$$sources, limit:60}' | \
	$(CURL) -H 'Content-Type: application/json' -d @- \
	-o coding.pdf '$(API)/api/rag/coding?format=pdf' && \
	echo "Wrote coding.pdf"
