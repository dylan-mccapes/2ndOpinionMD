import { generateJournalTimelinePdf } from '../pdfGenerator';

jest.mock('jspdf', () => {
  return jest.fn().mockImplementation(() => ({
    setFontSize: jest.fn(),
    setFont: jest.fn(),
    text: jest.fn(),
    addPage: jest.fn(),
    save: jest.fn(),
    output: jest.fn(() => 'mock-pdf-blob'),
    internal: {
      pageSize: {
        getWidth: jest.fn(() => 210),
        getHeight: jest.fn(() => 297)
      }
    }
  }));
});

describe('pdfGenerator', () => {
  test('smoke test: generates PDF with mixed symptom formats without throwing', async () => {
    const mockEntries = [
      {
        id: 1,
        date: '2025-08-17',
        symptoms: [
          'headache',
          { symptom: 'joint pain', severity: 7 },
          { name: 'fatigue', severity: 8 }
        ],
        ai_analysis: {
          analysis: 'Test analysis',
          symptoms: [
            'chronic headache',
            { symptom: 'joint stiffness', severity: 6 },
            { name: 'muscle aches' }
          ],
          diagnoses: [
            { name: 'Migraine', confidence: 0.8 }
          ]
        }
      },
      {
        id: 2,
        date: '2025-08-10',
        symptoms: [
          { symptom: 'brain fog', severity: 6 },
          { name: 'low energy', severity: 7 }
        ],
        ai_analysis: {
          analysis: 'Another analysis',
          symptoms: ['cognitive issues', 'fatigue'],
          diagnoses: []
        }
      }
    ];

    expect(async () => {
      await generateJournalTimelinePdf(mockEntries);
    }).not.toThrow();
  });

  test('smoke test: handles entries with no symptoms gracefully', async () => {
    const mockEntries = [
      {
        id: 1,
        date: '2025-08-17',
        symptoms: [],
        ai_analysis: {
          analysis: 'No symptoms reported',
          symptoms: [],
          diagnoses: []
        }
      }
    ];

    expect(async () => {
      await generateJournalTimelinePdf(mockEntries);
    }).not.toThrow();
  });

  test('smoke test: handles entries with null/undefined ai_analysis', async () => {
    const mockEntries = [
      {
        id: 1,
        date: '2025-08-17',
        symptoms: ['headache'],
        ai_analysis: null
      },
      {
        id: 2,
        date: '2025-08-16',
        symptoms: [{ symptom: 'fatigue', severity: 5 }],
        ai_analysis: undefined
      }
    ];

    expect(async () => {
      await generateJournalTimelinePdf(mockEntries);
    }).not.toThrow();
  });
});
