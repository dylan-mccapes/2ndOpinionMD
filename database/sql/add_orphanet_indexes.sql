-- Extra useful btree indexes (safe if already exist)
CREATE INDEX IF NOT EXISTS orphanet_phenos_orpha_idx ON ontology.orphanet_phenotype_links (orpha_code);
CREATE INDEX IF NOT EXISTS orphanet_phenos_hpo_idx   ON ontology.orphanet_phenotype_links (hpo_id);
CREATE INDEX IF NOT EXISTS orphanet_genes_orpha_idx  ON ontology.orphanet_gene_links (orpha_code);
CREATE INDEX IF NOT EXISTS orphanet_genes_symbol_idx ON ontology.orphanet_gene_links (gene_symbol);

