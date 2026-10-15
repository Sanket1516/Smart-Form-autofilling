import { formatValue } from '../../services/api';

const COLUMN_ORDER = [
  'code', 'name', 'max_marks', 'theory', 'practical', 'internal', 'practical_or_internal', 'total',
  'marks_obtained', 'grade', 'result', 'status',
  'date', 'description', 'reference', 'debit', 'credit', 'amount', 'balance',
  'relation', 'age', 'gender',
];

const HEADERS: Record<string, string> = {
  code: 'Code', name: 'Name', max_marks: 'Max', theory: 'Theory', practical: 'Practical', internal: 'Internal',
  practical_or_internal: 'Practical / internal', total: 'Total', marks_obtained: 'Obtained', grade: 'Grade',
  result: 'Result', status: 'Status', date: 'Date', description: 'Description', reference: 'Reference',
  debit: 'Debit', credit: 'Credit', amount: 'Amount (direction unknown)', balance: 'Balance',
  relation: 'Relation', age: 'Age', gender: 'Gender',
};

/** One row per record (subject, transaction, household member), values exactly as stored. */
export const RecordTable = ({ rows, caption }: { rows: Array<Record<string, unknown>>; caption: string }) => {
  const keys = new Set(rows.flatMap((row) => Object.keys(row)));
  const columns = [...COLUMN_ORDER.filter((key) => keys.has(key)), ...[...keys].filter((key) => !COLUMN_ORDER.includes(key))];
  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="tiny muted" style={{ textAlign: 'left' }}>{caption}</caption>
        <thead>
          <tr>{columns.map((key) => <th key={key}>{HEADERS[key] ?? key.replace(/_/g, ' ')}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((key) => <td key={key}>{formatValue(row[key])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
