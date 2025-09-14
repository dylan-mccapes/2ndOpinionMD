# server/api/mimic4_routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from .db import get_conn, put_conn

router = APIRouter(prefix="/api/mimic4", tags=["MIMIC-IV"])

# ---- Models
class DxItem(BaseModel):
    icd_code: str
    icd_version: int
    long_title: Optional[str] = None
    seq_num: Optional[int] = None

class Admission(BaseModel):
    hadm_id: int
    subject_id: int
    admittime: Optional[str] = None
    dischtime: Optional[str] = None
    admission_type: Optional[str] = None

class LabEvent(BaseModel):
    itemid: int
    label: str
    charttime: Optional[str] = None
    valuenum: Optional[float] = None
    valueuom: Optional[str] = None
    value: Optional[str] = None
    hadm_id: Optional[int] = None
    subject_id: Optional[int] = None

# ---- Endpoints

@router.get("/admission/{hadm_id}", response_model=Admission)
def get_admission(hadm_id: int):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
          SELECT hadm_id, subject_id, admittime, dischtime, admission_type
          FROM ehr_mimic4.admissions WHERE hadm_id=%s
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
def diagnoses(hadm_id: int = Query(..., description="Admission ID")):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
          SELECT d.icd_code, d.icd_version, dic.long_title, d.seq_num
          FROM ehr_mimic4.diagnoses_icd d
          LEFT JOIN ehr_mimic4.d_icd_diagnoses dic
            ON dic.icd_code=d.icd_code AND dic.icd_version=d.icd_version
          WHERE d.hadm_id=%s
          ORDER BY d.seq_num NULLS LAST, d.icd_version DESC, d.icd_code
        """, (hadm_id,))
        return [DxItem(icd_code=r[0], icd_version=r[1], long_title=r[2], seq_num=r[3]) for r in cur.fetchall()]
    finally:
        cur.close(); put_conn(conn)

@router.get("/cohort/icd", response_model=List[int])
def cohort_by_icd(
    icd_code_prefix: str = Query(..., description="ICD code prefix, e.g. 'I50'"),
    icd_version: int = Query(10, ge=9, le=10),
    limit: int = Query(1000, ge=1, le=10000)
):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
          SELECT DISTINCT hadm_id
          FROM ehr_mimic4.diagnoses_icd
          WHERE icd_version=%s
            AND icd_code LIKE %s
          LIMIT %s
        """, (icd_version, icd_code_prefix + '%', limit))
        return [r[0] for r in cur.fetchall()]
    finally:
        cur.close(); put_conn(conn)

@router.get("/labs", response_model=List[LabEvent])
def labs(
    hadm_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    label: Optional[str] = Query(None, description="LIKE match on d_labitems.label"),
    itemid: Optional[int] = None,
    since: Optional[str] = Query(None, description="ISO timestamp lower bound"),
    until: Optional[str] = Query(None, description="ISO timestamp upper bound"),
    limit: int = Query(200, ge=1, le=5000)
):
    if not any([hadm_id, subject_id, itemid, label]):
        raise HTTPException(400, "Provide at least one filter: hadm_id, subject_id, itemid, or label")
    conn = get_conn(); cur = conn.cursor()
    try:
        sql = """
          SELECT l.itemid, dl.label, l.charttime, l.valuenum, l.valueuom, l.value, l.hadm_id, l.subject_id
          FROM ehr_mimic4.labevents l
          JOIN ehr_mimic4.d_labitems dl USING (itemid)
          WHERE 1=1
        """
        params = []
        if hadm_id:   sql += " AND l.hadm_id=%s";   params.append(hadm_id)
        if subject_id:sql += " AND l.subject_id=%s";params.append(subject_id)
        if itemid:    sql += " AND l.itemid=%s";    params.append(itemid)
        if label:     sql += " AND dl.label ILIKE %s"; params.append(f"%{label}%")
        if since:     sql += " AND l.charttime >= %s"; params.append(since)
        if until:     sql += " AND l.charttime <= %s"; params.append(until)
        sql += " ORDER BY l.charttime DESC NULLS LAST LIMIT %s"; params.append(limit)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append(LabEvent(
                itemid=r[0], label=r[1],
                charttime=r[2].isoformat() if r[2] else None,
                valuenum=r[3], valueuom=r[4], value=r[5],
                hadm_id=r[6], subject_id=r[7]
            ))
        return out
    finally:
        cur.close(); put_conn(conn)

