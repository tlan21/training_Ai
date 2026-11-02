import type { components } from '../api-types';

type Category = components['schemas']['Category'];
export function isWideInterest(category: Category) {
    return category.name === 'Thể thao' || category.name === 'Phim ảnh';
}

// Keep DOM and visual order together when API ordering leaves a half row before a wide card.
export function layoutInterests(categories: Category[]) {
    const items = categories.filter(category => category.id);
    for (let index = 0, column = 0; index < items.length; index++) {
        if (isWideInterest(items[index]) && column === 1) {
            const next = items.findIndex((category, position) => position > index && !isWideInterest(category));
            if (next >= 0) items.splice(index, 0, ...items.splice(next, 1));
            else {
                items.splice(index - 1, 0, ...items.splice(index, 1));
                index--;
                column = 0;
            }
        }
        column = (column + (isWideInterest(items[index]) ? 2 : 1)) % 2;
    }
    return items;
}
