# server/api/mimic3_routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from .db import get_conn, put_conn

router = APIRouter(prefix="/api/mimic3", tags=["MIMIC-III"])

class DxItem(BaseModel):
    icd_code: str
    long_title: Optional[str] = None
    seq_num: Optional[int] = None

class Admission(BaseModel):
    hadm_id: int
    subject_id: int
    admittime: Optional[str] = None
    dischtime: Optional[str] = None
    admission_type: Optional[str] = None

@router.get("/admission/{hadm_id}", response_model=Admission)
def get_admission(hadm_id: int):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
          SELECT hadm_id, subject_id, admittime, dischtime, admission_type
          FROM ehr_mimic3.admissions WHERE hadm_id=%s
        """, (hadm_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, f"hadm_id {hadm_id} not found")
        return Admission(
            hadm_id=row[0], subject_id=row[1],
            admittime=row[2].isoformat() if row[2] else None,
            dischtime=row[3].isoformat() if row[3] else None,
            admission_type=row[4]
        )
    finally:
        cur.close(); put_conn(conn)

@router.get("/diagnoses", response_model=List[DxItem])
def diagnoses(hadm_id: int = Query(...)):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
          SELECT d.icd9_code, di.long_title, d.seq_num
          FROM ehr_mimic3.diagnoses_icd d
          LEFT JOIN ehr_mimic3.d_icd_diagnoses di USING (icd9_code)
          WHERE d.hadm_id=%s
          ORDER BY d.seq_num NULLS LAST, d.icd9_code
        """, (hadm_id,))
        return [DxItem(icd_code=r[0], long_title=r[1], seq_num=r[2]) for r in cur.fetchall()]
    finally:
        cur.close(); put_conn(conn)

