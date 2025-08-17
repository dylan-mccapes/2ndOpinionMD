import React from 'react';
import { normalizeStringList } from '../../utils/normalizeList';

export default function DiagnosisTable({ diagnoses }) {
  if (!Array.isArray(diagnoses) || diagnoses.length === 0) return null;

  const rows = diagnoses.map((d, i) => ({
    name: d?.name ?? '—',
    confidence: typeof d?.confidence === 'number' ? `${d.confidence}%` : '—',
    zone: d?.zone ?? '—',
    staxLevel: d?.staxLevel ?? '—',
    status: d?.status ?? '—',
    tags: normalizeStringList(d?.tags)
  }));

  return (
    <section className="diagnoses-section">
      <h4>Diagnoses</h4>
      <div className="table-wrapper">
        <table className="diagnosis-table">
          <thead>
            <tr>
              <th>Diagnosis</th>
              <th>Confidence</th>
              <th>Zone</th>
              <th>STAX</th>
              <th>Status</th>
              <th>Tags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
              <tr key={idx}>
                <td>{r.name}</td>
                <td>{r.confidence}</td>
                <td>{r.zone}</td>
                <td>{r.staxLevel}</td>
                <td>{r.status}</td>
                <td>
                  {r.tags.map((t, i) => (
                    <span key={i} className="tag-chip">{t}</span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
