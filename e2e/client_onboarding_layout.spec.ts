import { test, expect } from '@playwright/test';
import { isWideInterest, layoutInterests } from '../client/src/lib/onboarding';

test('INT-06 interest packing has no internal gaps and preserves API IDs and keyboard order', () => {
  for (let count = 0; count <= 8; count++) for (let mask = 0; mask < 2 ** count; mask++) {
    const categories = Array.from({ length: count }, (_, index) => ({ id: `cat_${index}`, name: mask & (1 << index) ? 'Thể thao' : 'Công nghệ' }));
    const before = JSON.stringify(categories);
    const items = layoutInterests(categories);
    expect(items.map(item => item.id).sort()).toEqual(categories.map(item => item.id).sort());
    expect(JSON.stringify(categories)).toBe(before);
    let column = 0;
    for (const item of items) {
      if (isWideInterest(item)) expect(column).toBe(0);
      column = (column + (isWideInterest(item) ? 2 : 1)) % 2;
    }
  }
  const categories = [{ id: 'cat_a', name: 'Bóng đá' }, { id: 'cat_b', name: 'Thể thao' }, { id: 'cat_c', name: 'Ca nhạc' }, { name: 'Invalid category' }];
  expect(layoutInterests(categories).map(item => item.id)).toEqual(['cat_a', 'cat_c', 'cat_b']);
});
