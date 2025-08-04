#!/usr/bin/env python3
"""
Unified HPO Data Loader
Orchestrates loading of HPO terms and disease associations
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
env_path = project_root / '.env'
load_dotenv(env_path)

sys.path.append(str(project_root))
from ontology_loaders.hpo.load_hpo_terms import HPOTermsLoader
from ontology_loaders.hpo.load_hpo_disease_links import HPODiseaseLinksLoader

async def load_hpo_data():
    """Load all HPO data"""
    print("🚀 Starting HPO data loading pipeline...")
    
    hp_json_path = "data/hpo/hp.json"
    phenotype_hpoa_path = "data/hpo/phenotype.hpoa"
    
    if not Path(hp_json_path).exists():
        print(f"❌ Error: {hp_json_path} not found")
        sys.exit(1)
    
    if not Path(phenotype_hpoa_path).exists():
        print(f"❌ Error: {phenotype_hpoa_path} not found")
        sys.exit(1)
    
    try:
        print("\n📋 Step 1: Loading HPO terms...")
        terms_loader = HPOTermsLoader()
        terms_count = await terms_loader.load_data(hp_json_path)
        
        print(f"✅ Loaded {terms_count} HPO terms")
        print(f"📊 Terms loading stats: {terms_loader.export_statistics()}")
        
        print("\n🔍 Validating HPO hierarchy...")
        hierarchy_valid = await terms_loader.validate_hierarchy()
        print(f"✅ Hierarchy validation: {'PASSED' if hierarchy_valid else 'FAILED'}")
        
        print("\n🔗 Step 2: Loading disease-phenotype associations...")
        links_loader = HPODiseaseLinksLoader()
        links_count = await links_loader.load_data(phenotype_hpoa_path)
        
        print(f"✅ Loaded {links_count} disease-phenotype associations")
        print(f"📊 Links loading stats: {links_loader.export_statistics()}")
        
        print(f"\n🎉 HPO data loading completed successfully!")
        print(f"📊 Summary:")
        print(f"   - HPO terms: {terms_count}")
        print(f"   - Disease associations: {links_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during HPO data loading: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(load_hpo_data())
    sys.exit(0 if success else 1)
