// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { RunStatusBadge } from './Badges';

describe('RunStatusBadge', () => {
  it('renders skipped scenes as an informational state', () => {
    const markup = renderToStaticMarkup(<RunStatusBadge status="skipped_no_clear_scene" />);

    expect(markup).toContain('No clear scene');
    expect(markup).toContain('bg-amber-50');
  });
});
