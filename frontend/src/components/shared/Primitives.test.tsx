// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { DataTable, StatCard } from './Primitives';

describe('shared primitives', () => {
  it('renders a stat card and a data table from fixture-shaped data', () => {
    const markup = renderToStaticMarkup(<><StatCard label="Detected area" value="1044 ha" /><DataTable items={[{ id: 'a1', name: 'PEKB' }]} getKey={(item) => item.id} columns={[{ key: 'name', label: 'Name', render: (item) => item.name }]} /></>);
    expect(markup).toContain('Detected area');
    expect(markup).toContain('PEKB');
  });
});
