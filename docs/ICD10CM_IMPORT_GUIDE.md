# ICD-10-CM Import Guide

This guide explains how to set up and run the ICD-10-CM data import for the 2ndOpinionMD knowledge graph.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- ICD-10-CM data file (`icd10cm-order-April-2025.txt`)

## Platform-Specific Setup

### macOS Setup

1. **Install PostgreSQL and Python:**
   ```bash
   brew install postgresql python3
   brew services start postgresql
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install psycopg2-binary python-dotenv
   ```

3. **Create database and schema:**
   ```bash
   psql postgres -c "CREATE DATABASE knowledgegraph;"
   psql -d knowledgegraph -f setup_knowledgegraph.sql
   ```

4. **Set database password (if needed):**
   ```bash
   psql postgres -c "ALTER USER $(whoami) PASSWORD 'postgres';"
   ```

### Linux (Ubuntu/Debian) Setup

1. **Install PostgreSQL and Python:**
   ```bash
   sudo apt update
   sudo apt install -y postgresql postgresql-contrib python3-pip
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install psycopg2-binary python-dotenv
   ```

3. **Create database and schema:**
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE knowledgegraph;"
   sudo cp setup_knowledgegraph.sql /tmp/
   sudo chmod 644 /tmp/setup_knowledgegraph.sql
   sudo -u postgres psql -d knowledgegraph -f /tmp/setup_knowledgegraph.sql
   ```

4. **Set postgres user password:**
   ```bash
   sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
   ```

## Running the Import

1. **Download the ICD-10-CM file** (if not already available)
2. **Run the import script:**
   ```bash
   python3 load_icd10cm.py /path/to/icd10cm-order-April-2025.txt
   ```

3. **Verify the import:**
   ```bash
   python3 verify_icd_import.py
   ```

## Expected Results

The import should load **97,584 ICD-10-CM codes** with:
- 1,917 root categories (codes without parents)
- 95,667 subcategories (codes with parent relationships)
- Full hierarchical paths (e.g., "A01 > A010 > A0100")

## Database Schema

The `ontology.icd` table contains:
- `code` (PRIMARY KEY) - ICD-10-CM codes
- `title` - Short descriptions
- `definition` - Long descriptions  
- `version` - Set to 'ICD-10-CM'
- `parent_code` - Parent code references
- `full_path` - Breadcrumb navigation paths
- `chapter`, `section` - Available for future use

## Troubleshooting

### Connection Issues
- **"password authentication failed"**: Ensure you set the postgres password
- **"peer authentication failed"**: Try connecting as the postgres user on Linux
- **"database does not exist"**: Run the database creation command first

### Permission Issues
- **"Permission denied"**: Copy files to `/tmp/` on Linux systems
- **"Module not found"**: Install dependencies with pip3/pip

### Data Issues
- **"File not found"**: Verify the path to your ICD-10-CM data file
- **"No records inserted"**: Check that the data file format matches expected structure

## File Structure

```
├── setup_knowledgegraph.sql    # Database schema setup
├── load_icd10cm.py            # Main import script
├── verify_icd_import.py       # Verification script
├── requirements.txt           # Python dependencies
└── ICD10CM_IMPORT_GUIDE.md   # This guide
```

## Sample Queries

After import, you can query the data:

```sql
-- View hierarchy for cholera codes
SELECT code, title, parent_code, full_path 
FROM ontology.icd 
WHERE code LIKE 'A00%' 
ORDER BY full_path;

-- Count codes by hierarchy level
SELECT 
  CASE WHEN parent_code IS NULL THEN 'Root' ELSE 'Child' END as level,
  COUNT(*) as count
FROM ontology.icd 
GROUP BY (parent_code IS NULL);
```
